from playwright.sync_api import sync_playwright
R={"cove_windansea":([32.8506,-117.2717],[32.8305,-117.2805]),"delmar15_solana":([32.9598,-117.2655],[32.9932,-117.2713])}
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page(viewport={"width":390,"height":844},device_scale_factor=2)
    pg.goto("http://localhost:8765/");pg.wait_for_function("window.ready===true",timeout=120000)
    for k,(a,c) in R.items(): print(k,pg.evaluate(f"testRoute({a},{c})"))
    pg.evaluate("testRoute([32.8506,-117.2717],[32.8305,-117.2805]);map.fitBounds([[32.826,-117.285],[32.853,-117.268]]);0");pg.wait_for_timeout(4000)
    pg.screenshot(path="/workspace/golfcart-maps/screenshot.png");b.close()
