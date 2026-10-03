from playwright.sync_api import sync_playwright
import sys
jobs=[("deck_solo.html","VisionGuard_Solo_Presentation_AbdulRafay.pdf",True),("deck_team.html","VisionGuard_Team_Presentation.pdf",True),
("train_solo.html","VisionGuard_Solo_Rehearsal_Training.pdf",False),("train_team.html","VisionGuard_Team_Rehearsal_Training.pdf",False)]
out="/home/user/Vision-Guard/docs/presentation/pdf/"
import os;os.makedirs(out,exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    pg=b.new_page()
    for h,o,deck in jobs:
        pg.goto("file:///tmp/claude-0/pdf/"+h); pg.wait_for_load_state("networkidle"); pg.evaluate("document.fonts.ready")
        pg.pdf(path=out+o, prefer_css_page_size=True, print_background=True,
               display_header_footer=not deck, header_template="<span></span>",
               footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#94A3B8;font-family:sans-serif">VisionGuard ULTRA · page <span class="pageNumber"></span> / <span class="totalPages"></span></div>')
        print(o)
    # screenshots for QA
    pg.set_viewport_size({"width":1280,"height":720})
    pg.goto("file:///tmp/claude-0/pdf/deck_team.html"); pg.wait_for_load_state("networkidle")
    for i in [0,6,9]:
        pg.evaluate(f"window.scrollTo(0,{i*720})"); pg.screenshot(path=f"/tmp/claude-0/pdf/shot{i}.png")
    b.close()
