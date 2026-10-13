"""Write the API's OpenAPI document for client generation."""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "api"))


def main() -> None:
    from app.main import app

    out = ROOT / "packages" / "api-client" / "openapi.json"
    out.write_text(json.dumps(app.openapi(), indent=2))
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
