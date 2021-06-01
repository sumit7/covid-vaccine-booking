from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
drawing = svg2rlg('captcha.svg')
renderPM.drawToFile(drawing, "captcha.png", fmt="PNG")
