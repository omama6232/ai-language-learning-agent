"""
Flat-vector (SVG) illustrations for the scenario quizzes.

Every scene is drawn in code (no image files, no internet needed), so the
quiz looks the same on every laptop. Each function returns one <svg> string.
Note: no blank lines inside the strings (Streamlit's markdown would end the
HTML block at a blank line).
"""


def _svg(inner: str) -> str:
    one_line = "".join(line.strip() for line in inner.strip().splitlines())
    return ('<svg viewBox="0 0 640 200" xmlns="http://www.w3.org/2000/svg" '
            'preserveAspectRatio="xMidYMid slice" style="width:100%;height:100%;display:block">'
            + one_line + "</svg>")


def _person(x, y, shirt, skin="#F2C6A0", hair="#2E2A2A", w=44, h=70):
    """A simple standing person: head + torso, feet at y+h."""
    return f"""
    <rect x="{x - w/2}" y="{y}" width="{w}" height="{h}" rx="16" fill="{shirt}"/>
    <rect x="{x - 6}" y="{y - 8}" width="12" height="12" fill="{skin}"/>
    <circle cx="{x}" cy="{y - 18}" r="15" fill="{skin}"/>
    <path d="M{x-15} {y-21} Q{x} {y-40} {x+15} {y-21} Q{x} {y-27} {x-15} {y-21}Z" fill="{hair}"/>
    """


def _plant(x, y, pot="#C9855B", leaf="#3E9B73"):
    return f"""
    <path d="M{x-14} {y} h28 l-4 28 h-20z" fill="{pot}"/>
    <ellipse cx="{x-9}" cy="{y-14}" rx="6" ry="16" fill="{leaf}" transform="rotate(-25 {x-9} {y-14})"/>
    <ellipse cx="{x+9}" cy="{y-16}" rx="6" ry="17" fill="{leaf}" transform="rotate(25 {x+9} {y-16})"/>
    <ellipse cx="{x}" cy="{y-20}" rx="6" ry="19" fill="#2F7F5C"/>
    """


def cafe() -> str:
    cups = "".join(f'<rect x="{50 + i*26}" y="46" width="14" height="16" rx="3" fill="#FFFFFF"/>'
                   f'<rect x="{62 + i*26}" y="50" width="4" height="8" rx="2" fill="#FFFFFF"/>' for i in range(5))
    lamps = "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="26" stroke="#2E3A3C" stroke-width="2"/>'
                    f'<path d="M{x-16} 44 A16 18 0 0 1 {x+16} 44Z" fill="#F2B84B"/>' for x in (300, 400, 500))
    return _svg(f"""
    <rect width="640" height="200" fill="#E9EFF0"/>
    <rect y="150" width="640" height="50" fill="#CBD5D7"/>
    <rect x="30" y="30" width="170" height="8" rx="3" fill="#8A6A4B"/>
    <rect x="30" y="66" width="170" height="8" rx="3" fill="#8A6A4B"/>
    <rect x="46" y="14" width="18" height="16" rx="3" fill="#B98B63"/><rect x="72" y="10" width="18" height="20" rx="3" fill="#8F6A4A"/>
    {cups}
    <rect x="230" y="22" width="120" height="70" rx="6" fill="#1F2D2E"/>
    <rect x="244" y="36" width="64" height="5" rx="2" fill="#F2B84B"/><rect x="244" y="50" width="86" height="4" rx="2" fill="#9FB6B8"/>
    <rect x="244" y="62" width="74" height="4" rx="2" fill="#9FB6B8"/><rect x="244" y="74" width="52" height="4" rx="2" fill="#9FB6B8"/>
    {lamps}
    {_person(150, 84, "#008B8B", hair="#4A2F22")}
    <rect x="0" y="122" width="400" height="78" fill="#5A7C7A"/>
    <rect x="0" y="114" width="410" height="12" rx="3" fill="#3F5C5A"/>
    <rect x="260" y="82" width="78" height="32" rx="5" fill="#A9B6B9"/><rect x="268" y="88" width="30" height="14" rx="3" fill="#2E3A3C"/>
    <rect x="310" y="96" width="14" height="18" fill="#2E3A3C"/>
    <rect x="30" y="98" width="22" height="16" rx="4" fill="#FFFFFF"/><rect x="50" y="102" width="6" height="8" rx="3" fill="#FFFFFF"/>
    <rect x="70" y="106" width="30" height="8" rx="3" fill="#F2B84B"/>
    <g fill="#2E3A3C"><ellipse cx="480" cy="140" rx="24" ry="7"/><rect x="476" y="146" width="8" height="50"/>
    <ellipse cx="560" cy="140" rx="24" ry="7"/><rect x="556" y="146" width="8" height="50"/></g>
    {_plant(612, 150)}
    """)


def airport() -> str:
    return _svg(f"""
    <defs><linearGradient id="skyA" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7EC8F0"/><stop offset="1" stop-color="#DDF1FB"/></linearGradient></defs>
    <rect width="640" height="200" fill="#E6EDF0"/>
    <rect x="20" y="16" width="380" height="132" fill="url(#skyA)"/>
    <rect x="20" y="118" width="380" height="30" fill="#9AA7AB"/>
    <rect x="20" y="132" width="380" height="3" fill="#F2F2F2"/>
    <g transform="translate(150 66)"><path d="M0 24 Q4 8 40 8 H150 Q176 12 182 24 Q176 36 150 38 H30 Q8 38 0 24Z" fill="#FFFFFF"/>
    <path d="M118 8 L150 -22 L162 -22 L146 8Z" fill="#E8735A"/><path d="M60 26 L108 54 L124 54 L96 26Z" fill="#D8E2E6"/>
    <path d="M56 12 L100 -12 L112 -12 L92 12Z" fill="#D8E2E6"/>
    <g fill="#5BA9D6"><circle cx="30" cy="22" r="3"/><circle cx="44" cy="22" r="3"/><circle cx="58" cy="22" r="3"/><circle cx="72" cy="22" r="3"/><circle cx="86" cy="22" r="3"/></g></g>
    <g stroke="#FFFFFF" stroke-width="5"><line x1="20" y1="16" x2="400" y2="16"/><line x1="20" y1="148" x2="400" y2="148"/><line x1="20" y1="16" x2="20" y2="148"/><line x1="400" y1="16" x2="400" y2="148"/><line x1="147" y1="16" x2="147" y2="148"/><line x1="274" y1="16" x2="274" y2="148"/></g>
    <rect y="150" width="640" height="50" fill="#B9C4C8"/>
    <rect x="430" y="22" width="190" height="82" rx="6" fill="#1F2D2E"/>
    <g fill="#F2B84B"><rect x="444" y="36" width="50" height="5" rx="2"/><rect x="444" y="54" width="50" height="5" rx="2"/><rect x="444" y="72" width="50" height="5" rx="2"/></g>
    <g fill="#9FD7D3"><rect x="510" y="36" width="90" height="5" rx="2"/><rect x="510" y="54" width="70" height="5" rx="2"/><rect x="510" y="72" width="80" height="5" rx="2"/></g>
    <rect x="440" y="140" width="46" height="36" rx="6" fill="#D9503F"/><rect x="456" y="132" width="14" height="9" rx="3" fill="none" stroke="#7B2E24" stroke-width="3"/>
    <rect x="496" y="146" width="40" height="32" rx="6" fill="#008B8B"/><rect x="509" y="139" width="14" height="9" rx="3" fill="none" stroke="#0A5A5A" stroke-width="3"/>
    <g fill="#2E3A3C"><circle cx="452" cy="180" r="4"/><circle cx="476" cy="180" r="4"/><circle cx="506" cy="182" r="4"/><circle cx="526" cy="182" r="4"/></g>
    {_person(585, 104, "#3E6FB0", hair="#222")}
    <rect x="566" y="110" width="12" height="38" rx="5" fill="#F2B84B"/>
    """)


def hospital() -> str:
    return _svg(f"""
    <rect width="640" height="200" fill="#E4F1F1"/>
    <rect y="152" width="640" height="48" fill="#C7D9DA"/>
    <rect x="40" y="28" width="46" height="46" rx="8" fill="#FFFFFF"/>
    <rect x="58" y="36" width="10" height="30" fill="#E8735A"/><rect x="48" y="46" width="30" height="10" fill="#E8735A"/>
    <circle cx="560" cy="52" r="26" fill="#FFFFFF" stroke="#8FB3B5" stroke-width="5"/>
    <line x1="560" y1="52" x2="560" y2="36" stroke="#2E3A3C" stroke-width="3"/><line x1="560" y1="52" x2="572" y2="58" stroke="#2E3A3C" stroke-width="3"/>
    <rect x="190" y="22" width="190" height="34" rx="6" fill="#008B8B"/>
    <rect x="206" y="35" width="90" height="6" rx="3" fill="#FFFFFF"/><rect x="206" y="45" width="60" height="4" rx="2" fill="#BFE6E3"/>
    {_person(255, 94, "#3E6FB0", hair="#3B2A20")}
    <rect x="150" y="124" width="220" height="62" rx="4" fill="#FFFFFF"/>
    <rect x="144" y="116" width="232" height="12" rx="4" fill="#008B8B"/>
    <rect x="300" y="100" width="58" height="16" rx="3" fill="#2E3A3C"/><rect x="310" y="116" width="38" height="4" fill="#2E3A3C"/>
    <rect x="170" y="104" width="30" height="12" rx="2" fill="#F2B84B"/>
    <rect x="440" y="96" width="46" height="84" rx="18" fill="#FFFFFF" stroke="#D2DEE0" stroke-width="2"/>
    <rect x="456" y="86" width="14" height="14" fill="#F2C6A0"/><circle cx="463" cy="72" r="16" fill="#F2C6A0"/>
    <path d="M447 70 Q463 44 479 70 Q463 60 447 70Z" fill="#5A3B2A"/>
    <path d="M452 104 Q463 138 474 104" fill="none" stroke="#2E3A3C" stroke-width="3"/><circle cx="463" cy="140" r="5" fill="#8FB3B5"/>
    <g fill="#8FB3B5"><rect x="20" y="132" width="86" height="12" rx="4"/><rect x="26" y="144" width="8" height="36"/><rect x="92" y="144" width="8" height="36"/>
    <rect x="30" y="110" width="76" height="22" rx="6" fill="#A8C6C8"/></g>
    {_plant(600, 142)}
    """)


def hotel() -> str:
    keys = "".join(f'<rect x="{200 + (i%4)*26}" y="{30 + (i//4)*24}" width="6" height="14" rx="2" fill="#F2B84B"/>'
                   f'<circle cx="{203 + (i%4)*26}" cy="{50 + (i//4)*24}" r="4" fill="#F2B84B"/>' for i in range(8))
    return _svg(f"""
    <rect width="640" height="200" fill="#F1E7DB"/>
    <rect y="154" width="640" height="46" fill="#C9B79E"/>
    <rect x="186" y="18" width="116" height="80" rx="6" fill="#6B4A33"/>
    {keys}
    <line x1="480" y1="0" x2="480" y2="24" stroke="#5A4635" stroke-width="2"/>
    <path d="M440 24 H520 L504 50 H456Z" fill="#F2B84B"/><circle cx="480" cy="54" r="6" fill="#FFE9A8"/>
    <rect x="30" y="30" width="90" height="62" rx="6" fill="#BFD9E6"/><line x1="75" y1="30" x2="75" y2="92" stroke="#FFFFFF" stroke-width="4"/><line x1="30" y1="61" x2="120" y2="61" stroke="#FFFFFF" stroke-width="4"/>
    {_person(250, 108, "#172D35", hair="#2A1E18")}
    <rect x="170" y="130" width="210" height="58" rx="4" fill="#8A5E3C"/>
    <rect x="162" y="122" width="226" height="12" rx="4" fill="#A9774D"/>
    <path d="M320 122 a10 9 0 0 1 20 0Z" fill="#F2B84B"/><rect x="326" y="114" width="8" height="4" fill="#F2B84B"/>
    <rect x="200" y="112" width="40" height="12" rx="2" fill="#FFFFFF"/>
    <rect x="450" y="120" width="120" height="6" rx="3" fill="#B98B33"/>
    <rect x="460" y="94" width="42" height="26" rx="4" fill="#008B8B"/><rect x="512" y="82" width="38" height="38" rx="4" fill="#E8735A"/>
    <path d="M452 120 v-62 h22" fill="none" stroke="#B98B33" stroke-width="4"/>
    <g fill="#2E3A3C"><circle cx="470" cy="136" r="6"/><circle cx="550" cy="136" r="6"/></g>
    <rect x="580" y="108" width="28" height="48" rx="3" fill="#C9855B"/>
    {_plant(610, 120)}
    """)


def office() -> str:
    skyline = "".join(f'<rect x="{30 + i*24}" y="{86 - h}" width="18" height="{h}" fill="{c}"/>'
                      for i, (h, c) in enumerate([(30, "#8FB6CC"), (52, "#7AA5BE"), (38, "#8FB6CC"), (62, "#6C98B3"), (44, "#8FB6CC"), (28, "#7AA5BE")]))
    return _svg(f"""
    <rect width="640" height="200" fill="#EBEFF1"/>
    <rect y="156" width="640" height="44" fill="#C3CED1"/>
    <rect x="20" y="20" width="190" height="70" fill="#CFE6F2"/>
    {skyline}
    <g stroke="#FFFFFF" stroke-width="5"><line x1="20" y1="20" x2="210" y2="20"/><line x1="20" y1="90" x2="210" y2="90"/><line x1="20" y1="20" x2="20" y2="90"/><line x1="210" y1="20" x2="210" y2="90"/><line x1="115" y1="20" x2="115" y2="90"/></g>
    <rect x="400" y="16" width="190" height="104" rx="6" fill="#FFFFFF" stroke="#B9C6C9" stroke-width="4"/>
    <g fill="#008B8B"><rect x="428" y="84" width="22" height="22"/><rect x="460" y="66" width="22" height="40"/><rect x="492" y="50" width="22" height="56" fill="#F2B84B"/><rect x="524" y="36" width="22" height="70"/></g>
    <rect x="428" y="30" width="60" height="5" rx="2" fill="#B9C6C9"/>
    <rect x="240" y="136" width="200" height="10" rx="3" fill="#8A5E3C"/><rect x="256" y="146" width="8" height="34" fill="#6B4A33"/><rect x="416" y="146" width="8" height="34" fill="#6B4A33"/>
    <rect x="300" y="104" width="64" height="4" fill="#4C5B5E"/><path d="M304 134 L296 104 H368 L360 134Z" fill="#2E3A3C"/><rect x="306" y="108" width="52" height="24" fill="#9FD7D3"/>
    <rect x="392" y="122" width="16" height="14" rx="3" fill="#FFFFFF"/><rect x="406" y="125" width="5" height="7" rx="2" fill="#FFFFFF"/>
    <rect x="236" y="108" width="40" height="28" rx="14" fill="#3E6FB0"/><rect x="226" y="140" width="22" height="10" fill="#2E3A3C"/>
    {_person(256, 92, "#E8735A", hair="#1E1A1A", w=38, h=44)}
    {_plant(30, 136)}
    """)


def bank() -> str:
    return _svg(f"""
    <rect width="640" height="200" fill="#E8EEF2"/>
    <rect y="154" width="640" height="46" fill="#C5CFD6"/>
    <circle cx="320" cy="22" r="18" fill="#F2B84B"/><circle cx="320" cy="22" r="13" fill="none" stroke="#B98B33" stroke-width="3"/>
    <text x="320" y="29" font-family="Arial,sans-serif" font-size="19" font-weight="700" text-anchor="middle" fill="#8A6A1E">$</text>
    <rect x="30" y="24" width="96" height="122" rx="8" fill="#5B6B72"/>
    <rect x="42" y="36" width="72" height="42" rx="4" fill="#9FD7D3"/><rect x="50" y="46" width="40" height="5" fill="#2E7D78"/><rect x="50" y="58" width="52" height="5" fill="#2E7D78"/>
    <rect x="42" y="90" width="72" height="22" rx="3" fill="#3F4C52"/><rect x="52" y="120" width="52" height="8" rx="2" fill="#1F2D2E"/>
    <rect x="200" y="106" width="300" height="80" fill="#2E5E8C"/><rect x="192" y="98" width="316" height="12" rx="3" fill="#1F4467"/>
    <rect x="212" y="40" width="276" height="60" fill="#CFE6F2" opacity=".55"/>
    <g stroke="#FFFFFF" stroke-width="4" fill="none"><rect x="212" y="40" width="276" height="60"/><line x1="350" y1="40" x2="350" y2="100"/></g>
    {_person(280, 62, "#008B8B", hair="#2A2220", w=42, h=40)}
    <rect x="262" y="94" width="38" height="8" rx="2" fill="#FFFFFF"/>
    <g fill="#2E3A3C"><rect x="544" y="104" width="6" height="48"/><rect x="590" y="104" width="6" height="48"/></g>
    <path d="M550 112 Q570 128 590 112" stroke="#D9503F" stroke-width="5" fill="none"/>
    <circle cx="547" cy="102" r="6" fill="#F2B84B"/><circle cx="593" cy="102" r="6" fill="#F2B84B"/>
    {_person(618, 88, "#3E6FB0", hair="#222", w=36)}
    """)


SCENES = {"cafe": cafe, "airport": airport, "hospital": hospital,
          "hotel": hotel, "office": office, "bank": bank}
