import os
import html

with open("loadbalancer/main.go", "r", encoding="utf-8") as f:
    lb_code = html.escape(f.read().strip())

with open("backend/main.go", "r", encoding="utf-8") as f:
    backend_code = html.escape(f.read().strip())

with open("client/main.go", "r", encoding="utf-8") as f:
    client_code = html.escape(f.read().strip())

header = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Distributed Systems Lab Report - Performance-Based Dynamic Load Balancer & Secure Group Chat</title>
    <style>
        @page {
            size: A4;
            margin: 16mm 16mm 16mm 16mm;
        }

        @media print {
            a {
                color: #0969da !important;
                text-decoration: underline !important;
            }
            .page-break {
                page-break-before: always;
            }
            .no-break {
                page-break-inside: avoid;
            }
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.5;
            color: #1f2328;
            background-color: #ffffff;
            margin: 0;
            padding: 0;
            font-size: 12.5px;
        }

        a {
            color: #0969da;
            text-decoration: underline;
            font-weight: 500;
        }

        a:hover {
            color: #0550ae;
        }

        .title-block {
            text-align: center;
            border-bottom: 2px solid #1f2328;
            padding-bottom: 14px;
            margin-bottom: 18px;
        }

        .title-block h1 {
            font-size: 20px;
            margin: 0 0 5px 0;
            color: #09264a;
            font-weight: 700;
        }

        .title-block h2 {
            font-size: 14px;
            margin: 0 0 12px 0;
            color: #4b5563;
            font-weight: 500;
            border: none;
            padding: 0;
        }

        .meta-table {
            width: 100%;
            max-width: 680px;
            margin: 0 auto;
            border-collapse: collapse;
        }

        .meta-table td {
            padding: 3px 10px;
            font-size: 12.5px;
            border: none;
        }

        .meta-table td.label {
            font-weight: 600;
            color: #374151;
            text-align: right;
            width: 25%;
        }

        .meta-table td.val {
            text-align: left;
            color: #111827;
            width: 25%;
        }

        .highlight-badge {
            display: inline-block;
            background-color: #ddf4ff;
            color: #0969da;
            border: 1px solid #54aeff;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 700;
            font-family: Consolas, monospace;
            font-size: 12.5px;
        }

        h2 {
            color: #0f172a;
            border-bottom: 1.5px solid #cbd5e1;
            padding-bottom: 3px;
            margin-top: 20px;
            margin-bottom: 8px;
            font-size: 15px;
            font-weight: 700;
        }

        h3 {
            color: #1e293b;
            margin-top: 12px;
            margin-bottom: 5px;
            font-size: 13px;
            font-weight: 600;
        }

        p {
            margin: 0 0 8px 0;
            text-align: justify;
        }

        ul, ol {
            margin: 0 0 8px 0;
            padding-left: 20px;
        }

        li {
            margin-bottom: 3px;
        }

        table.lab-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0 14px 0;
            font-size: 11.5px;
            page-break-inside: avoid;
        }

        table.lab-table th, table.lab-table td {
            border: 1px solid #cbd5e1;
            padding: 5px 8px;
            text-align: left;
        }

        table.lab-table th {
            background-color: #f1f5f9;
            color: #1e293b;
            font-weight: 600;
        }

        table.lab-table tr:nth-child(even) td {
            background-color: #f8fafc;
        }

        .method-tag {
            display: inline-block;
            padding: 1px 5px;
            border-radius: 3px;
            font-weight: 700;
            font-size: 10px;
            font-family: Consolas, monospace;
        }

        .tag-post { background-color: #dafbe1; color: #1a7f37; border: 1px solid #aceebb; }
        .tag-get { background-color: #ddf4ff; color: #0969da; border: 1px solid #54aeff; }

        .code-box {
            background-color: #f6f8fa;
            border: 1px solid #d0d7de;
            border-radius: 4px;
            padding: 6px 8px;
            font-family: Consolas, "Courier New", monospace;
            font-size: 11px;
            line-height: 1.35;
            margin: 6px 0 10px 0;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .source-code {
            background-color: #fbfcfd;
            border: 1px solid #d0d7de;
            border-radius: 4px;
            padding: 8px;
            font-family: Consolas, "Courier New", monospace;
            font-size: 9.5px;
            line-height: 1.3;
            overflow-x: auto;
            margin: 6px 0 12px 0;
            white-space: pre-wrap;
            word-break: break-all;
        }

        code.inline {
            background-color: #eff1f3;
            padding: 1px 4px;
            font-family: Consolas, monospace;
            font-size: 11.5px;
            border: 1px solid #d0d7de;
            border-radius: 3px;
            color: #b91c1c;
        }

        .image-box {
            margin: 12px 0;
            text-align: center;
            page-break-inside: avoid;
        }

        .image-box img {
            max-width: 96%;
            height: auto;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
        }

        .image-caption {
            font-size: 11px;
            color: #475569;
            margin-top: 4px;
            font-style: italic;
        }

        .callout {
            background-color: #f8fafc;
            border-left: 4px solid #0284c7;
            padding: 7px 10px;
            margin: 8px 0;
            font-size: 12px;
            page-break-inside: avoid;
        }

        .link-table td {
            vertical-align: middle;
        }

        .link-table td.url-cell {
            font-family: Consolas, monospace;
            font-size: 11px;
            word-break: break-all;
        }
    </style>
</head>
<body>

    <div class="title-block">
        <h1>Distributed Systems Lab Report</h1>
        <h2>Performance-Based Dynamic Load Balancer & End-to-End Secure Distributed Group Chat</h2>
        <table class="meta-table">
            <tr>
                <td class="label">Student Name:</td>
                <td class="val"><strong>Roshan Raj</strong></td>
                <td class="label">Roll Number:</td>
                <td class="val"><strong>12341830</strong></td>
            </tr>
            <tr>
                <td class="label">Submission URL:</td>
                <td class="val"><span class="highlight-badge"><a href="http://10.1.75.53:3297" target="_blank">http://10.1.75.53:3297</a></span></td>
                <td class="label">Course / Term:</td>
                <td class="val">Distributed Systems Lab</td>
            </tr>
        </table>
    </div>
"""
