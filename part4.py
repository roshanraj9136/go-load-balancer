def get_section_12(lb_code, backend_code, client_code):
    return f"""
    <div class="page-break"></div>

    <h2>12. Complete Source Code Listings</h2>
    <p>
        Below are the complete source code files for the Load Balancer (<code>loadbalancer/main.go</code>), Backend Service (<code>backend/main.go</code>), and Custom Load Generator (<code>client/main.go</code>). In strict compliance with assignment instructions, all code contains zero comments.
    </p>

    <h3>A. Load Balancer Implementation (loadbalancer/main.go)</h3>
    <div class="source-code">{lb_code}</div>

    <div class="page-break"></div>

    <h3>B. Backend Service Implementation (backend/main.go)</h3>
    <div class="source-code">{backend_code}</div>

    <div class="page-break"></div>

    <h3>C. Custom Benchmark Load Generator Implementation (client/main.go)</h3>
    <div class="source-code">{client_code}</div>

</body>
</html>
"""
