#!/usr/bin/env python3
"""Build an allowlisted portable release and a standalone PDF command guide."""
import hashlib
import io
import json
from pathlib import Path
import runpy
import tarfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2026.11.07.6'


def pdf_guide(text):
    lines = []
    for line in text.splitlines():
        plain = line.replace('`', '').replace('**', '').encode('ascii', 'replace').decode()
        lines.extend(textwrap.wrap(plain, width=100, replace_whitespace=False) or [''])
    pages = [lines[i:i + 62] for i in range(0, len(lines), 62)]
    objects = [None, None, b'<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>']
    page_ids = []
    for number, page in enumerate(pages, 1):
        page_id = len(objects) + 1
        content_id = page_id + 1
        page_ids.append(page_id)
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>'.encode())
        commands = ['BT', '/F1 8 Tf', '11 TL', '48 752 Td']
        for line in page:
            escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            commands.extend(['(' + escaped + ') Tj', 'T*'])
        commands.extend(['ET', 'BT /F1 8 Tf 48 30 Td', f'(Codex Workbench {VERSION} | Page {number}/{len(pages)}) Tj ET'])
        stream = '\n'.join(commands).encode()
        objects.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
    objects[0] = b'<< /Type /Catalog /Pages 2 0 R >>'
    kids = ' '.join(f'{number} 0 R' for number in page_ids)
    objects[1] = f'<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>'.encode()
    output = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f'{number} 0 obj\n'.encode() + body + b'\nendobj\n')
    start = len(output)
    output.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        output.extend(f'{offset:010d} 00000 n \n'.encode())
    output.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode())
    return bytes(output)


def main():
    destination = ROOT / 'artifacts' / VERSION
    destination.mkdir(parents=True, exist_ok=True)
    module = runpy.run_path(str(ROOT / 'workflow/install-portable.py'))
    payload = module['payload'](ROOT / 'workflow')
    files = {}
    for relative, data in payload.items():
        path = relative if relative.parts[0] == 'skills' else Path('workflow') / relative
        files[str(path)] = data
    for path in sorted((ROOT / 'scripts').glob('*.py')):
        files[str(path.relative_to(ROOT))] = path.read_bytes()
    for path in sorted((ROOT / 'tests').glob('*.py')):
        files[str(path.relative_to(ROOT))] = path.read_bytes()
    for name in ['commands-and-installation.md', 'guidance-coverage.md', 'code-mode.md', 'cross-host-resume.md', 'backlog.md', 'policy-upgrades.md', 'unified-providers.md', 'implementation-status.md', 'unattended-and-context.md', 'shared-project-handoff.md', 'quality-and-delivery.md', 'agent-workflow-research.md', 'one-page-guide.md', 'Codex-Workbench-One-Page.pdf']:
        files['docs/' + name] = (ROOT / 'docs' / name).read_bytes()
    files['LICENSE'] = (ROOT / 'LICENSE').read_bytes()
    files['requirements-claude.txt'] = (ROOT / 'requirements-claude.txt').read_bytes()
    files['README.md'] = ('# Codex Workbench ' + VERSION + '\n\n'
        'Read docs/commands-and-installation.md. Preview with `python3 workflow/install-portable.py`; '
        'apply with `python3 workflow/install-portable.py --apply`. Install/authenticate Codex separately. '
        'No credentials, user configuration, conversation state, or runtime data are bundled.\n').encode()
    manifest = {'version': VERSION, 'sha256': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}}
    files['RELEASE.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    archive = destination / ('codex-workbench-' + VERSION + '.tar.gz')
    with tarfile.open(archive, 'w:gz') as bundle:
        for name, data in sorted(files.items()):
            entry = tarfile.TarInfo('codex-workbench/' + name)
            entry.size = len(data)
            entry.mode = 0o644
            entry.mtime = 0
            bundle.addfile(entry, io.BytesIO(data))
    pdf = destination / 'Codex-Commands-and-Portable-Setup-Updated.pdf'
    pdf.write_bytes(pdf_guide((ROOT / 'docs/commands-and-installation.md').read_text()))
    one_page = destination / 'Codex-Workbench-One-Page.pdf'
    one_page.write_bytes((ROOT / 'docs/Codex-Workbench-One-Page.pdf').read_bytes())
    sums = ''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n' for path in [archive, pdf, one_page])
    (destination / 'SHA256SUMS').write_text(sums)
    print(json.dumps({'version': VERSION, 'archive': str(archive), 'guide_pdf': str(pdf), 'files': len(files)}))


if __name__ == '__main__':
    main()
