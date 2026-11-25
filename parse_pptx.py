import zipfile
import xml.etree.ElementTree as ET
import re

pptx = zipfile.ZipFile(r'k:\PROJECTS\RAHAT\INNOVATE FINALS PRESENTATION TEMPLATE.pptx')
slides = [name for name in pptx.namelist() if name.startswith('ppt/slides/slide') and name.endswith('.xml')]

def get_slide_num(name):
    m = re.search(r'slide(\d+)\.xml', name)
    return int(m.group(1)) if m else 0

slides.sort(key=get_slide_num)

text = ''
for slide in slides:
    xml = pptx.read(slide)
    tree = ET.fromstring(xml)
    text += '\n--- ' + slide + ' ---\n'
    for node in tree.iter():
        if node.text:
            text += node.text.strip() + ' '

print(text)
