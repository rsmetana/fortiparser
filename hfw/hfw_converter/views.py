
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from .forms import PolicyCliForm, NatCliForm

import json
import io
import pandas as pd

# ------------ Parsers (optional stubs) ------------
def parse_policy_blocks(cli_text: str):
    """
    Minimal stub: return a list of dicts expected by the template.
    Replace with your actual parser for 'show firewall policy' if desired.
    """
    # Example format expected in template:
    # [{'id': '1', 'srcintf': 'port1', 'dstintf': 'port2', 'action': 'accept',
    #   'srcaddr': 'LAN', 'dstaddr': 'ANY', 'service': 'HTTPS', 'comments': 'Example'}]
    return []

def parse_central_snat_blocks(cli_text: str):
    return []

def parse_vip_blocks(cli_text: str):
    return []

# ------------ Unified tabs handler ------------
@csrf_protect
def tabs_home(request):
    parsed_policies = request.session.get("parsed_policies", [])
    parsed_nat = request.session.get("parsed_nat", [])
    active_tab = "policies"

    policy_form = PolicyCliForm()
    nat_form = NatCliForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "parse_policies":
            active_tab = "policies"
            policy_form = PolicyCliForm(request.POST)
            if policy_form.is_valid():
                cli_text = policy_form.cleaned_data.get("policy_cli_text", "") or ""
                parsed_policies = parse_policy_blocks(cli_text)
                request.session["parsed_policies"] = parsed_policies
        elif action == "parse_nat":
            active_tab = "nat"
            nat_form = NatCliForm(request.POST)
            if nat_form.is_valid():
                # Client-side parsing is used; keep server session optional.
                cli_text = nat_form.cleaned_data.get("nat_cli_text", "") or ""
                request.session["parsed_nat"] = cli_text  # store raw text if desired

    return render(request, "hfw_converter/fortigate_tabs.html", {
        "policy_form": policy_form,
        "nat_form": nat_form,
        "parsed_data": parsed_policies,
        "parsed_nat": parsed_nat,
        "active_tab": active_tab,
    })

# ------------ Save endpoints ------------
@require_POST
@csrf_protect
def save_policies(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        policies = payload.get("policies", [])
        # TODO: persist to DB if needed
        return JsonResponse({"ok": True, "count": len(policies)})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

@require_POST
@csrf_protect
def save_nat(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        # payload may contain:
        #  - mode: 'central' or 'udt' (optional)
        #  - csnat: [...] central snat rows
        #  - vip:   [...] vip rows
        #  - udt:   [...] raw UDT rows
        # TODO: persist to DB if needed
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

# ------------ Export Excel endpoint ------------
@require_POST
@csrf_protect
def export_nat_excel(request):
    """
    Accepts JSON { csnat: [...], vip: [...] } and returns an Excel file with columns:
      ENA Public, Mapped Private, SNAT/DNAT, UDT Publics, Mapped Private, SNAT/DNAT

    Mapping:
      - Central SNAT rows:
          ENA Public     <- nat_ippool
          Mapped Private <- orig_addr
          SNAT/DNAT      <- "SNAT"
          UDT Publics    <- "" (blank)
          Mapped Private <- "" (duplicate col blank)
          SNAT/DNAT      <- "" (duplicate col blank)

      - VIP rows (DNAT):
          ENA Public     <- external_ip
          Mapped Private <- mapped_ip
          SNAT/DNAT      <- "DNAT"
          UDT Publics    <- protocol/extport if present else ""
          Mapped Private <- mapped_ip (duplicate to match requested header)
          SNAT/DNAT      <- "DNAT"     (duplicate to match requested header)
    """
    def as_str(x):
        if x is None: return ""
        if isinstance(x, (list, tuple)):
            return ",".join(str(i).strip() for i in x if i is not None)
        return str(x).strip()

    try:
        payload = json.loads(request.body.decode("utf-8"))
        csnat = payload.get("csnat", []) or []
        vip   = payload.get("vip", []) or []

        rows = []

        # Central SNAT rows
        for s in csnat:
            rows.append({
                "ENA Public": as_str(s.get("nat_ippool")),
                "Mapped Private": as_str(s.get("orig_addr")),
                "SNAT/DNAT": "SNAT",
                "UDT Publics": "",
                "Mapped Private.2": "",
                "SNAT/DNAT.2": ""
            })

        # VIP rows
        for v in vip:
            protocol = (v.get("protocol") or "").strip().lower()
            extport  = (v.get("external_port") or "").strip()
            udt_publics = ""
            if protocol and extport:
                udt_publics = f"{protocol}/{extport}"
            elif extport:
                udt_publics = extport

            mapped_ip = (v.get("mapped_ip") or "").strip()
            rows.append({
                "ENA Public": (v.get("external_ip") or "").strip(),
                "Mapped Private": mapped_ip,
                "SNAT/DNAT": "DNAT",
                "UDT Publics": udt_publics,
                "Mapped Private.2": mapped_ip,
                "SNAT/DNAT.2": "DNAT"
            })

        df = pd.DataFrame(rows, columns=[
            "ENA Public",
            "Mapped Private",
            "SNAT/DNAT",
            "UDT Publics",
            "Mapped Private.2",
            "SNAT/DNAT.2"
        ])

        # Force duplicate header names to match requested output
        df.rename(columns={
            "Mapped Private.2": "Mapped Private",
            "SNAT/DNAT.2": "SNAT/DNAT"
        }, inplace=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="NAT Summary")
        output.seek(0)

        resp = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        resp["Content-Disposition"] = 'attachment; filename="Fortigate_NAT.xlsx"'
        return resp

    except Exception as e:
        return HttpResponse(str(e), status=400)
