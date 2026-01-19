import re
from pathlib import Path

def inline_assets():
    dist_dir = Path("frontend/dist")
    index_path = dist_dir / "index.html"
    
    if not index_path.exists():
        print("❌ Error: frontend/dist/index.html not found. Run 'npm run build' first.")
        return

    content = index_path.read_text()
    
    # Inline CSS
    # <link rel="stylesheet" crossorigin href="/assets/index-hNH8n-MC.css">
    css_pattern = r'<link rel="stylesheet"[^>]*href="([^"]+)"[^>]*>'
    
    def repl_css(match):
        href = match.group(1)
        # href might be /assets/... or ./assets/...
        filename = Path(href).name
        # Find file in assets dir
        assets = list(dist_dir.glob(f"**/assets/{filename}"))
        if not assets:
            assets = list(dist_dir.glob(f"**/{filename}"))
            
        if assets:
            print(f"✅ Inlining CSS: {assets[0].name}")
            css_content = assets[0].read_text()
            return f'<style>\n{css_content}\n</style>'
        else:
            print(f"⚠️ Warning: CSS file not found for {href}")
            return match.group(0)

    content = re.sub(css_pattern, repl_css, content)

    # Inline JS
    # <script type="module" crossorigin src="/assets/index-DWFRgM31.js"></script>
    js_pattern = r'<script[^>]*src="([^"]+)"[^>]*></script>'
    
    def repl_js(match):
        src = match.group(1)
        filename = Path(src).name
        assets = list(dist_dir.glob(f"**/assets/{filename}"))
        if not assets:
            assets = list(dist_dir.glob(f"**/{filename}"))
            
        if assets:
            print(f"✅ Inlining JS: {assets[0].name}")
            js_content = assets[0].read_text()
            # Remove import/export if needed? Vite production build usually bundles everything.
            # But type="module" might be tricky if we inline without changing type?
            # Actually, standard <script> works better if code is bundled.
            # But let's keep type="module" if it was there, or just remove src.
            return f'<script type="module">\n{js_content}\n</script>'
        else:
            print(f"⚠️ Warning: JS file not found for {src}")
            return match.group(0)

    content = re.sub(js_pattern, repl_js, content)

    # Save back
    index_path.write_text(content)
    print(f"🎉 Successfully inlined assets into {index_path}")

if __name__ == "__main__":
    inline_assets()
