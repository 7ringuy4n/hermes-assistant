"""Dependency-free execution of the production Office archive preflight."""
import ast
from pathlib import Path
import re
import tempfile
from xml.etree import ElementTree
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    tree = ast.parse((ROOT / "architect/models/dispatcher/file_convert.py").read_text(encoding="utf-8"))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_check_office")
    env = {"Path": Path, "zipfile": zipfile, "ElementTree": ElementTree, "re": re, "MAX_EXPANDED": 1024}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "file_convert.py", "exec"), env)
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "sample.docx"
        fixtures = [
            ("safe inert hyperlink", "word/_rels/document.xml.rels", '<Relationships><Relationship Type="sample/hyperlink" TargetMode="External" Target="https://example.com"/></Relationships>', False),
            ("external image", "word/_rels/document.xml.rels", '<Relationships><Relationship Type="sample/image" TargetMode="External" Target="http://localhost/private"/></Relationships>', True),
            ("renamed macro payload relationship", "word/_rels/document.xml.rels", '<Relationships><Relationship Type="sample/vbaProject" Target="benign.bin"/></Relationships>', True),
            ("embedded active object", "word/_rels/document.xml.rels", '<Relationships><Relationship Type="sample/oleObject" Target="object.bin"/></Relationships>', True),
            ("external spreadsheet function", "xl/worksheets/sheet1.xml", '<worksheet xmlns="sample"><f>_xlfn.WEBSERVICE("http://localhost/private")</f></worksheet>', True),
            ("oversize archive expansion", "sample.txt", "x" * 2048, True),
        ]
        for index, (name, member, body, blocked) in enumerate(fixtures, 1):
            print(f"running test case {index}/{len(fixtures)} {name}")
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(member, body)
            try:
                env["_check_office"](path)
                assert not blocked, "unsafe Office source accepted"
            except ValueError:
                assert blocked, "safe Office source rejected"
    print("PASS production conversion security preflight")


if __name__ == "__main__":
    main()
