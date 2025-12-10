
from django import forms

class PolicyCliForm(forms.Form):
    policy_cli_text = forms.CharField(
        label="Paste FortiGate Policy CLI Output",
        widget=forms.Textarea(attrs={"rows": 12, "cols": 100}),
        required=False
    )

class NatCliForm(forms.Form):
    nat_cli_text = forms.CharField(
        label="Paste FortiGate NAT CLI Output (central-snat-map + vip)",
        widget=forms.Textarea(attrs={"rows": 12, "cols": 100}),
        required=False
    )
