from playwright.sync_api import sync_playwright
import os
T={"Max La Jolla pair":([32.8461,-117.2786],[32.8434,-117.2776]),
"Mission Beach -> PB (Crystal Pier)":([32.7740,-117.2520],[32.7975,-117.2573]),
"La Jolla Village -> Bird Rock":([32.8475,-117.2730],[32.8135,-117.2700]),
"Encinitas 101: Moonlight Beach -> Cardiff (Restaurant Row)":([33.0475,-117.2955],[33.0060,-117.2790]),
"Encinitas 101: Leucadia -> Swami's":([33.0650,-117.3030],[33.0345,-117.2930]),
"Cove -> Windansea":([32.8506,-117.2717],[32.8305,-117.2805]),
"Del Mar 15th -> Solana Beach station":([32.9598,-117.2655],[32.9932,-117.2713])}
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page();pg.goto(os.environ.get("URL","http://localhost:8765/"));pg.wait_for_function("window.ready===true",timeout=120000)
    for n,(a,c) in T.items(): print(n,"| legal:",pg.evaluate(f"testRoute({a},{c})"),"| risky:",pg.evaluate(f"testRoute({a},{c},true)"))
    b.close()
