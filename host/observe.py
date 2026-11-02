#!/usr/bin/env python3
"""Hosted adapter for public, scoped evidence. Never submits forms or follows links.

Not freestanding: stdlib HTTP/TLS, filesystem, hashlib and HTML parser are
explicitly HOSTED boundaries. core/ is separately freestanding and limited.
"""
import argparse
import datetime
import hashlib
import html.parser
import io
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

MAX_BYTES = 1_048_576
MAX_TARGETS = 4
ALLOWED_HOSTS = frozenset({
    'www.reisoffice.com.br', 'reisoffice.com.br',
    'www.cesarreis.com.br', 'cesarreis.com.br',
    'web.archive.org', 'www.geocities.ws',
})
CANDIDATE_URLS = (
    'https://www.reisoffice.com.br/',
    'https://www.cesarreis.com.br/',
    'https://www.geocities.ws/MotorCity/Track/1665/',
    'https://web.archive.org/web/20051215052151/http://www.cesarreis.com.br/',
)


def canon(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_url(url):
    if not isinstance(url, str) or len(url) > 1200 or any(ord(x) < 32 for x in url):
        raise ValueError('INVALID_URL')
    u = urllib.parse.urlsplit(url)
    if u.scheme != 'https' or u.username is not None or u.password is not None:
        raise ValueError('ONLY_HTTPS_WITHOUT_USERINFO')
    if u.hostname not in ALLOWED_HOSTS or u.port not in (None, 443):
        raise ValueError('HOST_NOT_ALLOWLISTED')
    if u.fragment or not u.path.startswith('/'):
        raise ValueError('INVALID_URL_PATH')
    if u.hostname == 'web.archive.org' and not u.path.startswith('/web/'):
        raise ValueError('ARCHIVE_PATH_NOT_ALLOWLISTED')
    if u.hostname == 'www.geocities.ws' and not u.path.startswith('/MotorCity/Track/1665/'):
        raise ValueError('GEOCITIES_SCOPE')
    if u.query:
        raise ValueError('QUERY_NOT_AUTHORIZED_FOR_COLLECTION')
    return u


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def retrieve(url):
    safe_url(url)
    opener = urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(url, headers={'User-Agent': 'RAFAELIA-WAYBACK-Evidence/0.1 (read-only; manual request)', 'Accept': 'text/html'})
    try:
        with opener.open(req, timeout=12) as resp:
            size = 0
            pieces = []
            while True:
                chunk = resp.read(min(16384, MAX_BYTES + 1 - size))
                if not chunk:
                    break
                pieces.append(chunk)
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError('BODY_EXCEEDS_SCOPE')
            return b''.join(pieces), {'status': resp.status, 'last_modified_unverified': resp.headers.get('Last-Modified'), 'content_type': resp.headers.get('Content-Type')}
    except urllib.error.HTTPError as exc:
        # Explicitly don't follow 3xx or promote 4xx/5xx to empty pages.
        return None, {'status': exc.code, 'error': 'HTTP_STATUS_NOT_CONTENT', 'last_modified_unverified': exc.headers.get('Last-Modified')}
    except Exception as exc:
        return None, {'status': 'TOKEN_VAZIO', 'error': type(exc).__name__}


class LinkMetadata(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.forms = []
        self.links = []
        self.meta_names = []
        self.images = 0
        self.scripts = 0
        self.includes_indicators = 0
        self.onsubmit = 0
        self.title_text = False
        self._title_parts = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'title':
            self.title_text = True
        elif tag == 'form':
            self.forms.append({'method_literal': (str(a.get('method', '')).upper() if str(a.get('method', '')).upper() in ('GET','POST') else 'UNKNOWN_OR_REDACTED'), 'onsubmit_present': 'onsubmit' in a,
                               'action_path_shape': self._path(a.get('action', ''))})
        elif tag == 'a' and 'href' in a:
            self.links.append(self._path(a['href']))
        elif tag == 'img':
            self.images += 1
        elif tag == 'script':
            self.scripts += 1
        elif tag == 'meta':
            self.meta_names.append(str(a.get('name', '')).lower() if str(a.get('name', '')).lower() in ('keywords','description','robots','viewport','author') else 'OTHER_REDACTED')
        if 'onsubmit' in a:
            self.onsubmit += 1

    def handle_endtag(self, tag):
        if tag == 'title':
            self.title_text = False

    def handle_data(self, data):
        if self.title_text:
            self._title_parts.append(data)

    @staticmethod
    def _path(v):
        # Paths are not emitted raw. Only file extension, scoped host, path hash, parameter names.
        if not isinstance(v, str):
            return {'extension': '', 'query_keys': [], 'path_sha256': sha(b''), 'host': 'EXTERNAL_REDACTED'}
        p = urllib.parse.urlsplit(v)
        ext = p.path.rsplit('/', 1)[-1].rsplit('.', 1)
        ext = (ext[-1].lower() if len(ext) > 1 else '')
        if not re.fullmatch('[a-z0-9]{1,8}', ext):
            ext = ''
        keys = sorted(set(k for k, _ in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
                          if re.fullmatch('[A-Za-z_]{1,32}', k)))[:32]
        return {'extension': ext, 'query_keys': keys, 'path_sha256': sha(p.path.encode('utf-8')),
                'host': p.hostname if p.hostname in ALLOWED_HOSTS else 'EXTERNAL_REDACTED'}

    def evidence(self):
        t = ' '.join(self._title_parts).strip()
        return {'form_count': len(self.forms), 'forms': self.forms[:50],
                'link_count': len(self.links), 'links_shape_sha256': sha(canon(self.links)),
                'link_shapes': sorted({json.dumps(x, sort_keys=True) for x in self.links})[:50],
                'meta_attribute_names': sorted(set(self.meta_names)),
                'meta_keywords_value': 'REDACTED_BY_DEFAULT',
                'title_sha256': sha(t.encode('utf-8')), 'title_value': 'REDACTED_BY_DEFAULT',
                'img_count': self.images, 'script_count': self.scripts, 'onsubmit_count': self.onsubmit,
                'server_include_source': 'TOKEN_VAZIO_NOT_OBSERVABLE_IN_RENDERED_HTML'}


def observe_bytes(url, body, headers, at):
    p = LinkMetadata()
    p.feed(body.decode('utf-8', errors='replace'))
    return {
        'url_scope': 'approved_public_root_or_archive',
        'source_url_sha256': sha(url.encode()),
        'captured_at_utc': at,
        'observed_http_status': headers['status'],
        'http_last_modified_claim': headers.get('last_modified_unverified') or 'TOKEN_VAZIO',
        'raw_body_sha256': sha(body), 'raw_body_sha3_256': hashlib.sha3_256(body).hexdigest(),
        'raw_size': len(body),
        'blake3': 'TOKEN_VAZIO_NOT_EXECUTED',
        'capture_class': 'HTTP_RESPONSE_BYTES_NOT_PROOF_OF_ORIGINAL_ASP_SOURCE',
        'html_indicators': p.evidence(),
        'claim_allowed': False,
    }


def write_receipt_once(output_dir, record):
    out = Path(output_dir)
    # no overwritten historical receipt and no symlink as output target
    if out.exists():
        raise FileExistsError('APPEND_ONLY_PATH_EXISTS')
    out.mkdir(parents=False, exist_ok=False)
    receipt = canon(record) + b'\n'
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(out / 'receipt.json', flags, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(receipt)
        f.flush()
        os.fsync(f.fileno())
    (out / 'SHA256SUMS').write_text(f'{sha(receipt)}  receipt.json\n', encoding='ascii')
    return sha(receipt)


def verify_previous(path, current_source_sha):
    file = Path(path)
    raw = file.read_bytes()
    expected_file = file.with_name('SHA256SUMS')
    line = expected_file.read_text(encoding='ascii').splitlines()[0]
    if line != f'{sha(raw)}  receipt.json':
        raise ValueError('PREVIOUS_RECEIPT_HASH_MISMATCH')
    r = json.loads(raw)
    if r.get('schema') != 'rafaelia.wayback.evidence.v1':
        raise ValueError('PREVIOUS_SCHEMA_INVALID')
    old = r.get('observation', {})
    if old.get('source_url_sha256') != current_source_sha:
        raise ValueError('PREVIOUS_SOURCE_MISMATCH')
    return sha(raw), old.get('raw_body_sha256')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=('synthetic', 'live'), default='synthetic')
    ap.add_argument('--target', choices=('reisoffice', 'cesarreis', 'geocities', 'cesarreis_2005'), default='geocities')
    ap.add_argument('--output', required=True)
    ap.add_argument('--manual-public-fetch-authorization', action='store_true')
    ap.add_argument('--previous-receipt', default=None)
    args = ap.parse_args(argv)
    at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if args.mode == 'live' and not args.manual_public_fetch_authorization:
        raise SystemExit('BLOCKED: HUMAN_PUBLIC_FETCH_AUTHORIZATION_REQUIRED')
    if args.mode == 'synthetic':
        data = b'<html><head><meta name="keywords" content="sample"></head><body><a href="Produtos.asp?Grupo=A&Pag=1">X</a></body></html>'
        observation = observe_bytes('synthetic://local', data, {'status': 200}, at)
        kind = 'SYNTHETIC_ONLY'
    else:
        url = CANDIDATE_URLS[('reisoffice','cesarreis','geocities','cesarreis_2005').index(args.target)]
        data, meta = retrieve(url)
        if data is None:
            observation = {'error': meta.get('error','TOKEN_VAZIO'), 'status': meta['status'],
                           'source_url_sha256': sha(url.encode()),
                           'content_integrity': 'TOKEN_VAZIO_NO_BODY', 'captured_at_utc': at}
            kind = 'FETCH_BLOCKED_NOT_ZERO'
        else:
            observation = observe_bytes(url, data, meta, at)
            kind = 'OBSERVED_HTTP_BYTES'
    previous_hash = 'TOKEN_VAZIO_NO_TRUSTED_ANCHOR'
    comparison = 'TOKEN_VAZIO_NO_PREVIOUS'
    if args.previous_receipt:
        previous_hash, old_body = verify_previous(args.previous_receipt, observation['source_url_sha256'])
        if old_body is None or 'raw_body_sha256' not in observation:
            comparison = 'TOKEN_VAZIO_NO_COMPARABLE_BODY'
        else:
            comparison = 'BYTE_IDENTICAL' if observation['raw_body_sha256'] == old_body else 'BYTE_CHANGED'
    receipt = {'schema': 'rafaelia.wayback.evidence.v1', 'kind': kind, 'producer': 'WAYBACK',
               'observation': observation, 'claim_allowed': False,
               'action': 'READ_ONLY_NO_FORM_SUBMIT', 'original_asp_source': 'TOKEN_VAZIO',
               'previous_receipt_sha256': previous_hash, 'byte_comparison': comparison,
               'anchor_integrity': 'TOKEN_VAZIO_NO_INDEPENDENT_SIGNATURE_OR_TIMESTAMP',
               'next': 'HUMAN_REVIEW_REQUIRED_FOR_ORIGINALITY_AND_CHAIN_ANCHOR'}
    digest = write_receipt_once(args.output, receipt)
    print(f'RECEIPT_SHA256={digest} STATUS={kind}')
    return 0 if kind != 'FETCH_BLOCKED_NOT_ZERO' else 3


if __name__ == '__main__':
    sys.exit(main())
