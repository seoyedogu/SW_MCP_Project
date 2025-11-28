from importlib import util
from pathlib import Path
spec = util.spec_from_file_location(
    "normalize_product_name",
    Path("fastapi/app/normalize_product_name.py"),
)
mod = util.module_from_spec(spec)
spec.loader.exec_module(mod)
print(mod.convert_product_name_to_model("삼성 블루스카이 5500"))
