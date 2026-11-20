import io
import json
import sys
import tempfile
import textwrap
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from archguard.cli import Io, run  # noqa: E402
from archguard.engine import analyze  # noqa: E402
from archguard.index import absolute  # noqa: E402
from archguard.policy import PolicyError, policy_hash, read_policy  # noqa: E402
from archguard.precommit import split  # noqa: E402
from archguard.selectors import matches_one, validate_selector  # noqa: E402

HEX = """\
schemaVersion: 2
language: python
roots: ["shop.**"]
profiles: [hexagonal]
allowEmptySelectors: true
roles:
  DOMAIN: ["shop.domain.**"]
  APPLICATION: ["shop.application.**"]
  OUTBOUND_PORT: ["shop.port.**"]
  INBOUND_ADAPTER: ["shop.web.**"]
  OUTBOUND_ADAPTER: ["shop.persistence.**"]
"""


class Project:
    def __init__(self, files, policy=HEX):
        self._tmp = tempfile.TemporaryDirectory(prefix='archguard-py-test-')
        self.root = Path(self._tmp.name)
        self.write('pyproject.toml', '[project]\nname = "shop-service"\n')
        self.write('architecture.yml', policy)
        for name, body in files.items():
            self.write(name, body)

    def write(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(body), encoding='utf-8')

    def analyze(self):
        return analyze(self.root, read_policy(self.root / 'architecture.yml'))

    def cli(self, *args, stdin='', today=None):
        out, err = io.StringIO(), io.StringIO()
        code = run(list(args), Io(self.root, out.write, err.write, lambda: stdin, today))
        return code, out.getvalue(), err.getvalue()

    def close(self):
        self._tmp.cleanup()


def rules(result, severity_floor=('WARNING', 'ERROR')):
    return sorted((f.rule_id, f.location.symbol, f.target) for f in result.findings if f.severity in severity_floor)


class AnalyzerTest(unittest.TestCase):
    def project(self, files, policy=HEX):
        p = Project(files, policy)
        self.addCleanup(p.close)
        return p

    # ---- selectors and resolution helpers ------------------------------------------------

    def test_selectors(self):
        self.assertTrue(matches_one('shop.domain.**', 'shop.domain'))
        self.assertTrue(matches_one('shop.domain.**', 'shop.domain.order'))
        self.assertFalse(matches_one('shop.domain.**', 'shop.domainx'))
        self.assertTrue(matches_one('**.api', 'a.b.api'))
        self.assertTrue(matches_one('shop.*.api', 'shop.orders.api'))
        self.assertFalse(matches_one('shop.*.api', 'shop.orders.v1.api'))
        for bad in ('', 'src/shop', 'shop..domain', 'shop.dom*', '.shop', 'a\\b'):
            with self.assertRaises(ValueError, msg=bad):
                validate_selector(bad)

    def test_relative_import_resolution(self):
        self.assertEqual(absolute('a.b', 1, 'c'), 'a.b.c')
        self.assertEqual(absolute('a.b', 2, 'c'), 'a.c')
        self.assertEqual(absolute('a.b', 2, None), 'a')
        self.assertIsNone(absolute('a.b', 3, 'c'))
        self.assertIsNone(absolute('', 1, 'x'))
        self.assertEqual(absolute('a', 0, 'x.y'), 'x.y')

    # ---- imports -------------------------------------------------------------------------

    def test_import_forms_and_rules(self):
        p = self.project({
            'src/shop/domain/__init__.py': '',
            'src/shop/domain/order.py': 'class Order: ...\n',
            'src/shop/port/store.py': 'from ..domain import order\n',
            'src/shop/persistence/sql.py': 'import sqlalchemy.orm\nfrom shop.port.store import *\n',
            'src/shop/application/place.py': '''\
                from shop.domain.order import Order
                from shop.persistence import sql
                ''',
        })
        result = p.analyze()
        self.assertEqual(rules(result), [
            ('HEX-002', 'shop.application.place', 'shop.persistence.sql'),
        ])
        evidence = [f.evidence for f in result.findings if f.rule_id == 'HEX-002']
        self.assertEqual(evidence, ['Module <shop.application.place> imports <shop.persistence.sql> (place.py:2)'])

    def test_domain_infrastructure_and_submodule_entries(self):
        p = self.project({
            'src/shop/domain/a.py': 'from sqlalchemy.orm import Session\n',
            'src/shop/domain/b.py': 'from http import client\n',
            'src/shop/domain/c.py': 'import sqlalchemyx\nimport httpx_mock\nfrom http import HTTPStatus\n',
            'src/shop/domain/d.py': 'def f():\n    import requests\n',
        })
        self.assertEqual(rules(p.analyze()), [
            ('HEX-001', 'shop.domain.a', 'sqlalchemy.orm'),
            ('HEX-001', 'shop.domain.b', 'http.client'),
            ('HEX-001', 'shop.domain.d', 'requests'),
        ])

    def test_type_checking_imports(self):
        files = {
            'src/shop/domain/order.py': '''\
                from typing import TYPE_CHECKING
                if TYPE_CHECKING:
                    from shop.persistence.sql import Row
                ''',
            'src/shop/persistence/sql.py': 'class Row: ...\n',
        }
        result = self.project(files).analyze()
        self.assertEqual(rules(result), [('HEX-001', 'shop.domain.order', 'shop.persistence.sql')])
        self.assertIn('imports type', result.findings[0].evidence)
        ignored = self.project(files, HEX + 'typeOnlyImports: ignore\n').analyze()
        self.assertEqual(rules(ignored), [])
        self.assertIn('Type-only imports ignored (typeOnlyImports: ignore): 1', ignored.diagnostics)

    def test_dynamic_imports(self):
        result = self.project({
            'src/shop/domain/order.py': '''\
                import importlib
                importlib.import_module('shop.persistence.sql')
                name = 'x'
                importlib.import_module(name)
                ''',
            'src/shop/persistence/sql.py': '',
        }).analyze()
        self.assertEqual(rules(result), [('HEX-001', 'shop.domain.order', 'shop.persistence.sql')])
        self.assertIn('dynamically imports', result.findings[0].evidence)
        self.assertIn('Computed dynamic imports not analyzed: 1', result.diagnostics)

    def test_unresolved_owned_import(self):
        files = {'src/shop/domain/order.py': 'from shop.domain.missing import X\nfrom ...outside import y\n'}
        with self.assertRaisesRegex(Exception, "Unresolved import of an owned module: 'from shop.domain.missing import X'"):
            self.project(files).analyze()
        result = self.project(files, HEX + 'unresolvedImports: warn\n').analyze()
        self.assertIn('Unresolved imports ignored (unresolvedImports: warn): 2', result.diagnostics)

    def test_namespace_folder_outside_roots_does_not_shadow_installed_package(self):
        result = self.project({
            'src/alembic/env.py': 'from alembic import context\n',
            'src/shop/persistence/migrate.py': 'from alembic import command\nimport alembic.config\n',
        }).analyze()
        self.assertEqual(result.dependencies, 2)
        self.assertTrue(any(d.startswith('Top-level namespace packages outside roots: alembic;') for d in result.diagnostics))

    def test_namespace_package_imports_are_not_dependencies(self):
        result = self.project({
            'src/shop/domain/model/order.py': '',
            'src/shop/application/use.py': 'import shop.domain.model\nfrom shop.domain import model\n',
        }).analyze()
        self.assertEqual(result.dependencies, 0)
        self.assertTrue(any(d.startswith('Imports of namespace packages') for d in result.diagnostics))

    def test_tests_and_hidden_directories_are_excluded(self):
        result = self.project({
            'src/shop/domain/order.py': '',
            'src/shop/domain/test_order.py': 'import requests\n',
            'src/shop/domain/tests/helpers.py': 'import requests\n',
            'src/shop/domain/conftest.py': 'import requests\n',
            'src/shop/domain/tests.py': 'import requests\n',
            'src/shop/domain/migrations/0001_initial.py': 'import requests\n',
            'src/gunicorn.conf.py': 'import requests\n',
            'src/shop/my-script.py': 'import requests\n',
            'src/shop/.venv/lib.py': 'import requests\n',
            'src/shop/domain/factories.py': 'from shop.domain.tests.helpers import x\nfrom shop.domain import test_order, tests\n',
        }).analyze()
        self.assertEqual(result.analyzed, 2)
        self.assertEqual(result.dependencies, 0)
        self.assertFalse(any('outside roots' in d for d in result.diagnostics))
        self.assertIn('Imports of excluded test modules not treated as dependencies: 3', result.diagnostics)

    def test_source_roots_and_ambiguous_modules(self):
        policy = HEX + 'sourceRoots: ["services/a", "services/b"]\n'
        p = self.project({'services/a/shop/domain/x.py': '', 'services/b/shop/domain/x.py': ''}, policy)
        with self.assertRaisesRegex(Exception, 'Ambiguous module name shop.domain.x'):
            p.analyze()
        with self.assertRaisesRegex(Exception, 'Source root not found'):
            self.project({'src/shop/domain/x.py': ''}, HEX + 'sourceRoots: ["lib"]\n').analyze()

    def test_cycle_between_packages_and_top_level_modules(self):
        policy = 'schemaVersion: 2\nlanguage: python\nroots: ["**"]\nrules:\n  CYCLE-001:\n    enabled: true\n'
        result = self.project({
            'alpha.py': 'import beta\n',
            'beta.py': 'import alpha\n',
            'pkg/one/m.py': 'from pkg.two import n\n',
            'pkg/two/n.py': 'from pkg.one import m\n',
        }, policy).analyze()
        cycles = sorted(f.evidence for f in result.findings if f.rule_id == 'CYCLE-001')
        self.assertEqual(len(cycles), 2)
        self.assertIn('alpha -> beta, beta -> alpha', cycles[0])
        self.assertIn('pkg.one -> pkg.two, pkg.two -> pkg.one', cycles[1])

    # ---- frameworks ----------------------------------------------------------------------

    def test_fastapi_entity_exposure_variants(self):
        result = self.project({
            'src/shop/persistence/models.py': '''\
                from sqlalchemy.orm import declarative_base, Mapped
                from sqlalchemy import Column, Integer
                Base = declarative_base()
                class Product(Base):
                    __tablename__ = "products"
                    id = Column(Integer, primary_key=True)
                class Audit(Base):
                    id: Mapped[int]
                class Mixin(Base):
                    __abstract__ = True
                    id: Mapped[int]
                ''',
            'src/shop/persistence/__init__.py': 'from .models import Product as Product\n',
            'src/shop/web/schemas.py': 'from pydantic import BaseModel\nclass ProductDto(BaseModel):\n    id: int\n',
            'src/shop/web/api.py': '''\
                from typing import Annotated, List, Optional
                from fastapi import APIRouter, Body, Depends
                from shop.persistence import Product
                from shop.persistence.models import Audit, Mixin
                from shop.web.schemas import ProductDto
                router = APIRouter()

                @router.get("/a", response_model=List[Product])
                def a(): ...

                @router.post("/b")
                async def b(body: Annotated["Audit", Body()]) -> Optional[ProductDto]: ...

                @router.get("/c")
                def c(x: Mixin | None = None) -> ProductDto: ...

                @router.get("/d")
                def d(user: Product = Depends(), *, audit: Annotated[Audit, Depends()]) -> ProductDto: ...

                def helper(p: Product) -> Product: ...
                ''',
        }).analyze()
        exposures = sorted((f.location.symbol, f.location.line, f.evidence) for f in result.findings if f.rule_id == 'FW-002')
        self.assertEqual(exposures, [
            ('shop.web.api#a', 9, 'HTTP method <shop.web.api#a> exposes persistence entity <shop.persistence.models#Product>'),
            ('shop.web.api#b', 12, 'HTTP method <shop.web.api#b> exposes persistence entity <shop.persistence.models#Audit>'),
        ])
        tags = {f.location.symbol: f.evidence for f in result.findings if f.rule_id == 'MODEL-002'}
        self.assertIn('fastapi.endpoint', tags['shop.web.api'])
        self.assertIn('pydantic.model', tags['shop.web.schemas'])
        self.assertIn('persistence.entity', tags['shop.persistence.models'])

    def test_flask_sqlmodel_and_django(self):
        result = self.project({
            'src/shop/persistence/db.py': 'from flask_sqlalchemy import SQLAlchemy\ndb = SQLAlchemy()\n',
            'src/shop/persistence/user.py': '''\
                from .db import db
                class User(db.Model):
                    id = db.Column(db.Integer, primary_key=True)
                ''',
            'src/shop/persistence/hero.py': '''\
                from sqlmodel import SQLModel, Field
                class HeroBase(SQLModel):
                    name: str
                class Hero(HeroBase, table=True):
                    id: int = Field(primary_key=True)
                ''',
            'src/shop/web/views.py': '''\
                from flask import Blueprint
                from shop.persistence.user import User
                from shop.persistence.hero import Hero, HeroBase
                bp = Blueprint("users", __name__)

                @bp.route("/users/<int:id>")
                def show(id: int) -> User: ...

                @bp.get("/heroes")
                def heroes() -> list[HeroBase]: ...

                @bp.post("/heroes")
                def create(hero: Hero) -> HeroBase: ...
                ''',
            'src/shop/application/django_models.py': '''\
                from django.db import models
                class Base(models.Model):
                    class Meta:
                        abstract = True
                class Order(Base):
                    pass
                ''',
        }, HEX + 'rules:\n  HEX-001:\n    enabled: false\n').analyze()
        exposures = sorted((f.location.symbol, f.target) for f in result.findings if f.rule_id == 'FW-002')
        self.assertEqual(exposures, [
            ('shop.web.views#create', 'shop.persistence.hero'),
            ('shop.web.views#show', 'shop.persistence.user'),
        ])
        tags = {f.location.symbol: f.evidence for f in result.findings if f.rule_id == 'MODEL-002'}
        self.assertIn('flask.endpoint', tags['shop.web.views'])
        self.assertIn('persistence.entity', tags['shop.application.django_models'])

    def test_django_and_drf_endpoints_outside_adapters(self):
        result = self.project({
            'src/shop/application/views.py': 'from django.http import JsonResponse\ndef index(request):\n    return JsonResponse({})\n',
            'src/shop/application/api.py': '''\
                from rest_framework import viewsets
                class OrderViewSet(viewsets.ModelViewSet):
                    pass
                ''',
            'src/shop/application/base.py': 'from django.views.generic import TemplateView\nclass Page(TemplateView):\n    pass\n',
            'src/shop/application/pages.py': 'from .base import Page\nclass Home(Page):\n    pass\n',
            'src/shop/application/urls.py': 'urlpatterns = []\n',
            'src/shop/web/ok.py': 'from rest_framework.decorators import api_view\n@api_view(["GET"])\ndef ok(request): ...\n',
        }, HEX + 'rules:\n  HEX-001:\n    enabled: false\n').analyze()
        fw1 = sorted(f.location.symbol for f in result.findings if f.rule_id == 'FW-001')
        self.assertEqual(fw1, ['shop.application.api', 'shop.application.base', 'shop.application.pages', 'shop.application.views'])

    def test_fw001_points_at_the_route_decorator(self):
        result = self.project({
            'src/shop/application/main.py': 'from fastapi import FastAPI\napp = FastAPI()\n\n\n@app.get("/")\nasync def root():\n    return {}\n',
        }).analyze()
        [f] = [f for f in result.findings if f.rule_id == 'FW-001']
        self.assertEqual(f.location.line, 5)

    # ---- policy --------------------------------------------------------------------------

    def test_policy_validation(self):
        cases = {
            'roots: ["a.**"]\nroots: ["b.**"]\n': 'Duplicate key',
            'roots: ["a.**"]\nprofiles: ~\n': 'null',
            'roots: ["src/a/**"]\n': 'dotted module names',
            'roots: ["a.**"]\nunknownKey: 1\n': r'Unknown policy key at \(root\): unknownKey',
            'roots: ["a.**"]\nprofiles: [nope]\n': 'Policy schema violation|Unknown architecture profile',
            'roots: ["a.**"]\nsourceRoots: ["../x"]\n': 'project-relative',
        }
        for body, message in cases.items():
            p = self.project({}, 'schemaVersion: 2\nlanguage: python\n' + body)
            with self.assertRaisesRegex(Exception, message, msg=body):
                read_policy(p.root / 'architecture.yml')
        ts = self.project({}, 'schemaVersion: 2\nlanguage: typescript\nroots: ["src/**"]\n')
        with self.assertRaisesRegex(PolicyError, "language 'typescript'"):
            read_policy(ts.root / 'architecture.yml')
        v1 = self.project({}, 'schemaVersion: 1\nroots: ["a.."]\n')
        with self.assertRaises(PolicyError):
            read_policy(v1.root / 'architecture.yml')

    def test_extends_locked_rules_and_org_presets(self):
        preset = 'schemaVersion: 2\nkind: preset\nlanguage: python\nprofiles: [hexagonal]\nrules:\n  HEX-001:\n    locked: true\n    severity: ERROR\n'
        p = self.project({'base.yml': preset}, 'schemaVersion: 2\nlanguage: python\nextends: ["./base.yml"]\nroots: ["shop.**"]\n')
        policy = read_policy(p.root / 'architecture.yml')
        self.assertEqual(policy.profiles, ['hexagonal'])
        p.write('architecture.yml', 'schemaVersion: 2\nlanguage: python\nextends: ["./base.yml"]\nroots: ["shop.**"]\nrules:\n  HEX-001:\n    severity: WARNING\n')
        with self.assertRaisesRegex(PolicyError, 'locked'):
            read_policy(p.root / 'architecture.yml')
        p.write('site/acme_archguard_presets/__init__.py', '')
        p.write('site/acme_archguard_presets/presets/base/1.0.0.yml', preset)
        p.write('architecture.yml', 'schemaVersion: 2\nlanguage: python\nextends: ["org:acme/base@1.0.0"]\nroots: ["shop.**"]\n')
        sys.path.insert(0, str(p.root / 'site'))
        self.addCleanup(sys.path.remove, str(p.root / 'site'))
        self.assertEqual(read_policy(p.root / 'architecture.yml').profiles, ['hexagonal'])
        p.write('architecture.yml', 'schemaVersion: 2\nlanguage: python\nextends: ["org:nobody/base@1.0.0"]\nroots: ["shop.**"]\n')
        with self.assertRaisesRegex(PolicyError, 'nobody_archguard_presets'):
            read_policy(p.root / 'architecture.yml')

    def test_policy_hash_is_order_insensitive_for_profiles(self):
        a = self.project({}, 'schemaVersion: 2\nlanguage: python\nroots: ["a.**"]\nprofiles: [hexagonal, ddd]\n')
        b = self.project({}, 'schemaVersion: 2\nlanguage: python\nroots: ["a.**"]\nprofiles: [ddd, hexagonal]\n')
        self.assertEqual(policy_hash(read_policy(a.root / 'architecture.yml')), policy_hash(read_policy(b.root / 'architecture.yml')))

    # ---- fingerprints, debt, CLI ---------------------------------------------------------

    def test_fingerprint_ignores_line_numbers(self):
        files = {'src/shop/domain/order.py': 'import requests\n'}
        first = self.project(files).analyze().findings[0].fingerprint
        moved = self.project({'src/shop/domain/order.py': '\n\n\nimport requests\n'}).analyze().findings[0]
        self.assertEqual(moved.location.line, 4)
        self.assertEqual(first, moved.fingerprint)

    def test_cli_gate_baseline_suppressions_and_changed_files(self):
        p = self.project({'src/shop/domain/order.py': 'import requests\n', 'src/shop/domain/other.py': 'import redis\n'})
        code, out, err = p.cli('check', '--format', 'agent')
        self.assertEqual(code, 1, err)
        lines = [json.loads(line) for line in out.splitlines()]
        self.assertEqual(lines[-1], {'summary': True, 'status': 'FAILED', 'new': 2, 'existing': 0, 'suppressed': 0})
        self.assertEqual(p.cli('baseline')[0], 0)
        self.assertEqual(p.cli('baseline')[0], 2)
        p.write('architecture.yml', HEX + 'newOnly: true\n')
        code, _, err = p.cli('check', '--baseline', 'architecture-baseline.json')
        self.assertEqual(code, 2, 'policy changed: baseline must be regenerated')
        self.assertIn('Baseline schema, engine or policy does not match', err)
        self.assertEqual(p.cli('baseline', '--overwrite-baseline')[0], 0)
        code, _, err = p.cli('check', '--baseline', 'architecture-baseline.json')
        self.assertEqual(code, 0, err)
        report = json.loads((p.root / 'reports/archguard/archguard.json').read_text())
        self.assertEqual({f['status'] for f in report['findings'] if f['severity'] != 'INFO'}, {'EXISTING'})
        self.assertTrue((p.root / 'reports/archguard/archguard.sarif').is_file())
        self.assertTrue((p.root / 'reports/archguard/index.html').is_file())

        p.write('architecture.yml', HEX)
        fingerprint = next(f['fingerprint'] for f in report['findings'] if f['location']['symbol'] == 'shop.domain.order')
        suppressions = {'schemaVersion': 1, 'entries': [{'fingerprint': fingerprint, 'owner': 'team', 'reason': 'legacy', 'expires': '2030-01-01'}]}
        p.write('suppressions.json', json.dumps(suppressions))
        code, out, _ = p.cli('check', '--suppressions', 'suppressions.json', '--format', 'agent', '--changed-files', '-',
                             stdin='src/shop/domain/order.py\n')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.splitlines()[-1])['suppressed'], 1)
        code, _, err = p.cli('check', '--suppressions', 'suppressions.json', today=date(2031, 1, 1))
        self.assertEqual(code, 2)
        self.assertIn('Expired suppression', err)

    def test_cli_errors_never_pass(self):
        p = self.project({'src/shop/domain/order.py': 'def broken(:\n'})
        code, out, err = p.cli('check', '--format', 'json,agent')
        self.assertEqual(code, 2)
        self.assertIn('Cannot parse src/shop/domain/order.py:1', err)
        self.assertEqual(json.loads(out)['status'], 'ERROR')
        self.assertEqual(json.loads((p.root / 'reports/archguard/archguard.json').read_text())['analysisStatus'], 'FAILED')
        self.assertEqual(p.cli('check', '--format', 'pdf')[0], 64)
        self.assertEqual(p.cli('frobnicate')[0], 64)
        self.assertEqual(p.cli('--config')[0], 64)
        empty = self.project({'src/other/x.py': ''})
        code, _, err = empty.cli('check')
        self.assertEqual(code, 2)
        self.assertIn('refusing a vacuous pass', err)

    def test_cli_validate_rules_version(self):
        p = self.project({})
        code, out, _ = p.cli('validate')
        self.assertEqual(code, 0)
        self.assertIn('Policy valid', out)
        code, out, _ = p.cli('rules', '--json')
        ids = {r['id'] for r in json.loads(out)}
        self.assertTrue({'HEX-001', 'FW-002', 'CYCLE-001'} <= ids)
        code, out, _ = p.cli('--version')
        self.assertIn('python analyzer', out)

    def test_module_id_from_pyproject(self):
        result = self.project({'src/shop/domain/order.py': 'import requests\n'}).analyze()
        self.assertEqual(result.findings[0].location.module, 'shop-service')
        self.assertEqual(result.findings[0].location.path, 'src/shop/domain/order.py')
        self.assertFalse(any('falls back' in d for d in result.diagnostics))

        nested = self.project({'svc/pyproject.toml': '[tool.poetry]\nname = "svc-dist"\n',
                               'svc/shop/domain/order.py': 'import requests\n'},
                              HEX + 'sourceRoots: ["svc"]\n')
        (nested.root / 'pyproject.toml').unlink()
        result = nested.analyze()
        self.assertEqual(result.findings[0].location.module, 'svc-dist')
        self.assertFalse(any('falls back' in d for d in result.diagnostics))

        bare = self.project({'src/shop/domain/order.py': 'import requests\n'})
        (bare.root / 'pyproject.toml').unlink()
        result = bare.analyze()
        self.assertEqual(result.findings[0].location.module, bare.root.name)
        self.assertTrue(any('falls back' in d for d in result.diagnostics))

    def test_precommit_argument_split(self):
        self.assertEqual(split(['--config', 'a.yml', 'x.py', 'y.py']), (['--config', 'a.yml'], ['x.py', 'y.py']))
        self.assertEqual(split(['--format=agent', '--', '--weird.py']), (['--format=agent'], ['--weird.py']))


if __name__ == '__main__':
    unittest.main()
