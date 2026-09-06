import os
import subprocess
import html

import part1
import part2
import part3
import part4

with open("D:/go-load-balancer/loadbalancer/main.go", "r", encoding="utf-8") as f:
    lb_code = html.escape(f.read().strip())

with open("D:/go-load-balancer/backend/main.go", "r", encoding="utf-8") as f:
    backend_code = html.escape(f.read().strip())

with open("D:/go-load-balancer/client/main.go", "r", encoding="utf-8") as f:
    client_code = html.escape(f.read().strip())

full_html = (
    part1.header +
    part2.sections_1_to_6 +
    part3.sections_7_to_11 +
    part4.get_section_12(lb_code, backend_code, client_code)
)

html_path = "D:/go-load-balancer/report.html"
pdf_path = "D:/go-load-balancer/Final_Lab_Report.pdf"

with open(html_path, "w", encoding="utf-8") as f:
    f.write(full_html)

print(f"Written report.html ({len(full_html)} bytes)")

edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
cmd = [
    edge_exe,
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={pdf_path}",
    html_path
]

res = subprocess.run(cmd, capture_output=True, text=True)
print(f"Edge exit code: {res.returncode}")

if os.path.exists(pdf_path):
    print(f"Generated PDF: {pdf_path} ({os.path.getsize(pdf_path)} bytes)")
else:
    print("PDF generation failed!")
