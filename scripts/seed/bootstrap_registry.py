from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

if __name__ == '__main__':
    print('bootstrap registry placeholder')
    print(f'definitions root: {ROOT / "definitions"}')
