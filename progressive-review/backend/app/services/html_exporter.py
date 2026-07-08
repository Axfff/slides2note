import json

from app.models.review_ir import ProgressiveReviewIR


class HTMLExporter:
    def export(self, ir: ProgressiveReviewIR) -> str:
        ir_json = json.dumps(ir.model_dump(mode="json"), ensure_ascii=False)
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{ir.title}</title>
</head>
<body>
  <main>
    <h1>{ir.title}</h1>
    <pre id="ir"></pre>
  </main>
  <script>
    const ir = {ir_json};
    document.getElementById("ir").textContent = JSON.stringify(ir, null, 2);
  </script>
</body>
</html>"""

