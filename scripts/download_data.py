"""Download ONLY the official MC1 archive; retain original files for traceability."""
import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path

URL = 'https://raw.githubusercontent.com/vast-challenge/2026-data/main/VAST_Challenge_2026_MC1.zip'
ROOT = Path(__file__).resolve().parents[1]


def extract(archive, destination):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            target = (destination / entry.filename).resolve()
            if not target.is_relative_to(destination): raise ValueError('Archive path escapes data/raw')
        z.extractall(destination)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,help='Offline official ZIP');args=ap.parse_args()
    raw=ROOT/'data/raw';raw.mkdir(parents=True,exist_ok=True)
    archive=raw/'VAST_Challenge_2026_MC1.zip'
    if args.archive:
        if args.archive.resolve()!=archive.resolve(): shutil.copyfile(args.archive,archive)
    else:
        temp=archive.with_suffix('.zip.part')
        with urllib.request.urlopen(URL,timeout=90) as r, temp.open('wb') as f: shutil.copyfileobj(r,f)
        if not zipfile.is_zipfile(temp): raise ValueError('Official URL did not return ZIP')
        temp.replace(archive)
    extract(archive,raw)
    print('Official source:',URL);print('Extracted to',raw)

if __name__=='__main__': main()
