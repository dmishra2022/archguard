"""Copy the language-neutral spec catalog into the package so the distribution is self-contained."""
import shutil
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SOURCE = PACKAGE.parent.parent / 'spec'
TARGET = PACKAGE / 'src' / 'archguard' / 'spec'

shutil.rmtree(TARGET, ignore_errors=True)
TARGET.mkdir(parents=True)
shutil.copy2(SOURCE / 'index.yml', TARGET / 'index.yml')
for part in ('profiles', 'rules', 'infrastructure', 'schemas'):
    shutil.copytree(SOURCE / part, TARGET / part)
print(f'Copied spec catalog to {TARGET}')
