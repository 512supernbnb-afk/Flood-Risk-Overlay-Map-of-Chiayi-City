# ==========================================
# 嘉義市 韌性設施 + SSP 情境地圖（完整重構版）
# Folium / GeoPandas
# ==========================================

import pandas as pd
import geopandas as gpd
import folium
import json
from pathlib import Path
from datetime import datetime
from branca.colormap import LinearColormap

# ==========================================
# 1. 路徑設定（請修改成你的資料夾）
# ==========================================
BASE_DIR = Path(r"C:\Users\aboon\OneDrive\桌面\Piethon html")

DATA_DIR = BASE_DIR / "data"
SSP_DIR = DATA_DIR / "ssp"
FACILITY_DIR = DATA_DIR / "facility"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_HTML = OUTPUT_DIR / f"嘉義市韌性設施地圖_{datetime.now().strftime('%Y%m%d')}.html"

# ==========================================
# 2. 基本設定
# ==========================================
TARGET_CRS = "EPSG:4326"

MAP_CENTER = [23.480, 120.449]

# SSP 情境
SSP_FILES = {
    "1.5°C": SSP_DIR / "嘉義市_最小統計區_AR6_T1.5.shp",
    "2.0°C": SSP_DIR / "嘉義市_最小統計區_AR6_T2.0.shp",
    "4.0°C": SSP_DIR / "嘉義市_最小統計區_AR6_T4.0.shp"
}

# 設施分類
FACILITY_TYPES = [
    "身心障礙",
    "老人福利機構",
    "托嬰中心",
    "兒童福利",
    "警察單位",
    "消防單位",
    "醫療處所",
    "避難收容",
    "人行地下道",
    "橋梁",
    "車行地下道",
    "雨水下水管管線",
    "雨水下水管人手孔",
    "加油站"
]

# ==========================================
# 3. 初始化地圖
# ==========================================
m = folium.Map(
    location=MAP_CENTER,
    zoom_start=13,
    control_scale=True,
    tiles=None
)

street = folium.TileLayer(
    tiles="CartoDB positron",
    name="街道路線圖",
    control=False,
    show=True
)
street.add_to(m)

osm = folium.TileLayer(
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr="OSM",
    name="OSM街道圖",
    control=False,
    show=True
).add_to(m)

sat = folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="衛星圖",
    control=False,
    show=False
)
sat.add_to(m)

# ==========================================
# 4. SSP 色帶
# ==========================================
COLOR_DICT = {
    1: "#FEF87B",
    2: "#FECE7C",
    3: "#FDA07B",
    4: "#FD7B7B",
    5: "#C47B7B"
}

DEPTH_MAP = {
    1.0: "0.3–0.5 公尺",
    2.0: "0.5–1.0 公尺",
    3.0: "1.0–2.0 公尺",
    4.0: "2.0–3.0 公尺",
    5.0: "> 3.0 公尺"
}
# ==========================================
# 5. 載入 SSP 圖層
# ==========================================
city = gpd.read_file(r"C:\Users\aboon\OneDrive\桌面\Piethon html\data\borderline\嘉義市界.shp")

if city.crs is None:
    city.set_crs(epsg=3826, inplace=True)

city = city.to_crs(TARGET_CRS)

folium.GeoJson(
    city,
    style_function=lambda x:{
        "color":"#111",
        "weight":3,
        "fillOpacity":0
    }
).add_to(m)

ssp_meta = []

for label, shp_path in SSP_FILES.items():

    if not shp_path.exists():
        print(f"找不到檔案：{shp_path}")
        continue

    gdf = gpd.read_file(shp_path, encoding="utf-8").to_crs(TARGET_CRS)
    gdf["flood_text"] = gdf["v_lv"].map(DEPTH_MAP)

    # datetime 清理
    for col in gdf.columns:
        if str(gdf[col].dtype).startswith("datetime"):
            gdf[col] = gdf[col].astype(str)

    # 找欄位
    risk_field = None
    for c in gdf.columns:
        if "眾數_HV" in c:
            risk_field = c
            break

    if risk_field is None:
        raise Exception(f"{label} 找不到眾數_HV欄位")

    max_val = float(gdf[risk_field].max())

    fg = folium.FeatureGroup(
        name=label,
        overlay=False,
        show=(label == "1.5°C"),
        control=False
    )

    def style_func(feature):
        v = feature["properties"][risk_field]

        return {
            "fillColor": COLOR_DICT.get(int(v), "#cccccc"),
            "color": "#444",
            "weight": 0.5,
            "fillOpacity": 0.75
        }

    folium.GeoJson(
        gdf,
        style_function=style_func,
        tooltip=folium.GeoJsonTooltip(
            fields=[risk_field, "flood_text"],
            aliases=["危害-脆弱度等級:", "可能淹水深度："],
            sticky=True,
            localize=True
        )
    ).add_to(fg)

    fg.add_to(m)

    ssp_meta.append({
        "js_name": fg.get_name(),
        "label": label,
        "max_prob": max_val
    })

# ==========================================
# 6. 載入設施圖層
# ==========================================
# ==========================================
# 6. 載入設施圖層（點資料 PNG icon版）
# ==========================================

ICON_MAP = {
    "身心障礙": "disability.png",
    "老人福利機構": "elder.png",
    "托嬰中心": "baby.png",
    "兒童福利": "child.png",
    "警察單位": "police.png",
    "消防單位": "fire.png",
    "醫療處所": "hospital.png",
    "避難收容": "shelter.png",
    "人行地下道": "walkway.png",
    "橋梁": "bridge.png",
    "車行地下道": "tunnel.png",
    "加油站": "gas.png"
}

facility_meta = []

for fac in FACILITY_TYPES:

    # ==================================================
    # 未分類圖層
    # ==================================================
    normal_file = FACILITY_DIR / f"{fac}_未分類.geojson"

    if normal_file.exists():

        gdf = gpd.read_file(normal_file)
        count = len(gdf)
        if gdf.crs is None:
            gdf.set_crs(epsg=3826, inplace=True)

        gdf = gdf.to_crs(TARGET_CRS)

        for col in gdf.columns:
            if str(gdf[col].dtype).startswith("datetime"):
                gdf[col] = gdf[col].astype(str)

        fg = folium.FeatureGroup(
            name=f"{fac}_未分類",
            overlay=True,
            show=False,
            control=False
        )

        icon_file = ICON_MAP.get(fac, "default.png")

        for _, row in gdf.iterrows():

            geom = row.geometry

            if geom is None:
                continue

            gtype = geom.geom_type

    # =========================
    # 自動抓名稱
    # =========================
            name = "未命名"

            for col in ["名稱", "NAME", "name", "機構名稱", "單位名稱", "機構名", "橋梁名", "單位別"]:
                if col in row.index:
                    val = row[col]

                    if pd.notna(val) and str(val).strip() != "":
                        name = str(val)
                        break

            popup_html = f"""
            <div style="font-family:Microsoft JhengHei;font-size:13px;">
            <b>名稱：</b>{name}<br>
            <b>類型：</b>{fac}<br>
            <b>狀態：</b>
            <span style='color:#2ecc71;font-weight:bold;'>未分類</span>
            </div>
            """

    # ====================================
    # Point
    # ====================================
            if gtype == "Point":

                folium.Marker(
                    location=[geom.y, geom.x],

                    icon=folium.CustomIcon(
                        icon_image=f"icons/{icon_file}",
                        icon_size=(28, 28),
                        icon_anchor=(14, 14)
                    ),

                    tooltip=f"{fac}_未分類",

                    popup=folium.Popup(
                        popup_html,
                        max_width=260
                    )

                ).add_to(fg)

    # ====================================
    # Line
    # ====================================
            elif gtype in ["LineString", "MultiLineString"]:

                folium.GeoJson(

                    geom,

                    style_function=lambda x: {
                        "color": "#ff8800",
                        "weight": 4,
                        "opacity": 0.9
                    },

                    tooltip=f"{fac}_未分類",

                    popup=folium.Popup(
                        popup_html,
                        max_width=260
                    )

                ).add_to(fg)

    # ====================================
    # Polygon
    # ====================================
            elif gtype in ["Polygon", "MultiPolygon"]:

                folium.GeoJson(

                    geom,

                    style_function=lambda x: {
                        "fillColor": "#2ecc71",
                        "color": "#1e8449",
                        "weight": 1,
                        "fillOpacity": 0.4
                    },

                    tooltip=f"{fac}_未分類",

                    popup=folium.Popup(
                        popup_html,
                        max_width=260
                    )

                ).add_to(fg)

        fg.add_to(m)

        facility_meta.append({
            "js_name": fg.get_name(),
            "label": f"{fac}_未分類"
        })

    # ==================================================
    # 有風險圖層
    # ==================================================
    risk_file = FACILITY_DIR / f"{fac}_有風險.geojson"

    if risk_file.exists():

        gdf = gpd.read_file(risk_file)

        if gdf.crs is None:
            gdf.set_crs(epsg=3826, inplace=True)

        gdf = gdf.to_crs(TARGET_CRS)

        for col in gdf.columns:
            if str(gdf[col].dtype).startswith("datetime"):
                gdf[col] = gdf[col].astype(str)

        fg = folium.FeatureGroup(
            name=f"{fac}_有風險",
            overlay=True,
            show=False,
            control=False
        )

        icon_file = ICON_MAP.get(fac, "default.png")

        for _, row in gdf.iterrows():

            geom = row.geometry

            if geom is None:
                continue

            gtype = geom.geom_type

    # =========================
    # 自動抓名稱
    # =========================
            name = "未命名"

            for col in ["名稱", "NAME", "name", "機構名稱", "單位名稱", "機構名", "橋梁名", "單位別"]:
                if col in row.index:
                    val = row[col]

                    if pd.notna(val) and str(val).strip() != "":
                        name = str(val)
                        break

            popup_html = f"""
            <div style="font-family:Microsoft JhengHei;font-size:13px;">
            <b>名稱：</b>{name}<br>
            <b>類型：</b>{fac}<br>
            <b>狀態：</b>
            <span style='color:#2ecc71;font-weight:bold;'>未分類</span>
            </div>
            """

    # ====================================
    # Point
    # ====================================
            if gtype == "Point":

                folium.Marker(
                    location=[geom.y, geom.x],

                    icon=folium.CustomIcon(
                        icon_image=f"icons/{icon_file}",
                        icon_size=(28, 28),
                        icon_anchor=(14, 14)
                    ),

                    tooltip=f"{fac}_未分類",

                    popup=folium.Popup(
                        popup_html,
                        max_width=260
                    )
        
                ).add_to(fg)

    # ====================================
    # Line
    # ====================================
            elif gtype in ["LineString", "MultiLineString"]:

                folium.GeoJson(

                    geom,
        
                    style_function=lambda x: {
                        "color": "#ff3333",
                        "weight": 4,
                        "opacity": 0.9
                    },

                    tooltip=f"{fac}_未分類",

                    popup=folium.Popup(
                        popup_html,
                        max_width=260
                    )

                ).add_to(fg)

    # ====================================
    # Polygon
    # ====================================
            elif gtype in ["Polygon", "MultiPolygon"]:

                folium.GeoJson(
        
                    geom,

                    style_function=lambda x: {
                        "fillColor": "#e74c3c",
                        "color": "#1e8449",
                        "weight": 1,
                        "fillOpacity": 0.4
                    },

                    tooltip=f"{fac}_未分類",

                    popup=folium.Popup(
                        popup_html,
                        max_width=260
                    )

                ).add_to(fg)
        
        fg.add_to(m)

        facility_meta.append({
            "js_name": fg.get_name(),
            "label": f"{fac}_有風險"
        })


# ==========================================
# 7. 自訂 UI
# ==========================================

print(ssp_meta)
print(facility_meta[:3])
print(len(facility_meta))



ui = """
<div id="panel" class="map-panel">

<div id="toggle-btn">☰</div>

<div class="title">嘉義市韌性設施風險圖</div>

<div class="section">
<div class="label">底圖模式</div>
<select id="base-select" class="select">
<option value="osm">OSM街道圖</option>
<option value="street">街道路線圖</option>
<option value="sat">衛星圖</option>
</select>
</div>

<div class="section">
<div class="label">危害-脆弱度 升溫情境</div>
<select id="ssp-select" class="select"></select>
</div>

<div class="section">
<div class="label">韌性設施</div>
<div id="facility-box"></div>
</div>

<button id="reset-btn" class="btn">重設視圖</button>

</div>

<style>

summary {
    list-style: none;
}

summary::-webkit-details-marker {
    display: none;  /* 隱藏原本三角形 */
}

.arrow {
    display: inline-block;
    transition: transform 0.25s ease;
    margin-right: 6px;
}

details[open] .arrow {
    transform: rotate(90deg);
}

.map-panel{
position:fixed;
top:20px;
right:20px;
z-index:9999;
width:300px;
max-height:85vh;
overflow:hidden;
background:rgba(255,255,255,0.95);
backdrop-filter: blur(6px);
padding:16px;
border-radius:12px;
box-shadow:0 6px 20px rgba(0,0,0,0.25);
font-family:Segoe UI,Microsoft JhengHei;
}

#toggle-btn{
position:absolute;
top:8px;
right:10px;
cursor:pointer;
font-size:18px;
}

.map-panel.collapsed{
width:45px;
height:45px;
overflow:hidden;
padding:8px;
}

.map-panel.collapsed *:not(#toggle-btn){
display:none;
}

.title{
font-size:18px;
font-weight:600;
margin-bottom:14px;
}

.section{
margin-bottom:14px;
}

.label{
font-size:13px;
font-weight:600;
margin-bottom:6px;
}

.select{
width:100%;
padding:7px;
border-radius:6px;
border:1px solid #ccc;
}

#facility-box{

max-height:260px;

overflow-y:auto;
overflow-x:hidden;

padding:8px;

border:1px solid #d6dce5;
border-radius:8px;

background:#fafbfd;

scrollbar-width:thin;

}

/* Chrome scrollbar */
#facility-box::-webkit-scrollbar{
width:8px;
}

#facility-box::-webkit-scrollbar-thumb{
background:#b8c2cc;
border-radius:10px;
}

#facility-box::-webkit-scrollbar-track{
background:transparent;
}

details{
margin-bottom:6px;
}

summary{
cursor:pointer;
font-weight:600;
}

.btn{
width:100%;
padding:9px;
border:none;
background:#2c7be5;
color:white;
border-radius:6px;
cursor:pointer;
}

.btn:hover{
background:#1a5fd0;
}

</style>

<script>

var mapObj;
var sspMeta = __SSP__;
var facMeta = __FAC__;

function getLayer(name){
    try{return window[name];}
    catch{return null;}
}

function initUI(){

    mapObj = __MAP__;

    var osm = __OSM__;
    var street = __STREET__;
    var sat = __SAT__;
    document.getElementById("toggle-btn").onclick = function(){

        let panel = document.getElementById("panel");

        panel.classList.toggle("collapsed");

    }
    // ------------------
    // 底圖切換
    // ------------------
    document.getElementById("base-select").onchange=function(){

        mapObj.removeLayer(osm);
        mapObj.removeLayer(street);
        mapObj.removeLayer(sat);

        if(this.value=="osm") mapObj.addLayer(osm);
        if(this.value=="street") mapObj.addLayer(street);
        if(this.value=="sat") mapObj.addLayer(sat);
    }

    // ------------------
    // SSP
    // ------------------
    let s = document.getElementById("ssp-select");

    s.innerHTML = sspMeta.map(x =>
        `<option value="${x.label}">${x.label}</option>`
    ).join("");

    function clearSSP(){
        sspMeta.forEach(i=>{
            let l = getLayer(i.js_name);
            if(l) mapObj.removeLayer(l);
        });
    }

    s.onchange=function(){
        clearSSP();
        let f = sspMeta.find(x=>x.label==this.value);
        if(f) mapObj.addLayer(getLayer(f.js_name));
    }

    // ------------------
    // 設施分組
    // ------------------
    let groups = {};

    facMeta.forEach(f=>{
        let sp = f.label.split("_");
        let base = sp[0];
        let type =
            sp.length > 1
            ? sp.slice(1).join("_")
            : "未分類";

        if(!groups[base]) groups[base]=[];

        groups[base].push({
            label:f.label,
            type:type,
            js_name:f.js_name
        });
    });

    let html="";

    for(let g in groups){

        html+=`
        <details>
          <summary>
            <span class="arrow">▶</span> ${g}
          </summary>
        `;

        groups[g].forEach(i=>{
            html+=`
            <label>
            <input type="checkbox" value="${i.label}">
            ${i.type}
            </label><br>`;
        });

        html+="</details>";
    }

    document.getElementById("facility-box").innerHTML=html;

    document.querySelectorAll("#facility-box input").forEach(cb=>{
        cb.onchange=function(){

            let f = facMeta.find(x=>x.label==this.value);
            if(!f) return;

            let lyr = getLayer(f.js_name);

            if(this.checked) mapObj.addLayer(lyr);
            else mapObj.removeLayer(lyr);
        }
    });

    // ------------------
    // Reset
    // ------------------
    document.getElementById("reset-btn").onclick=function(){

        mapObj.setView([23.480,120.449],13);

        document.getElementById("base-select").value="osm";

        s.value="1.5°C";
        s.onchange();

        document.querySelectorAll("#facility-box input").forEach(cb=>{
            cb.checked=false;
            let f = facMeta.find(x=>x.label==cb.value);
            if(f){
                let lyr=getLayer(f.js_name);
                mapObj.removeLayer(lyr);
            }
        });
    }

    // 預設
    s.value="1.5°C";
    s.onchange();

}

setTimeout(initUI,1200);

</script>
"""

# ===== 用 replace 注入（避免 f-string 問題） =====
ui = ui.replace("__MAP__", m.get_name())
ui = ui.replace("__SSP__", json.dumps(ssp_meta, ensure_ascii=False))
ui = ui.replace("__FAC__", json.dumps(facility_meta, ensure_ascii=False))
ui = ui.replace("__OSM__", osm.get_name())
ui = ui.replace("__STREET__", street.get_name())
ui = ui.replace("__SAT__", sat.get_name())

m.get_root().html.add_child(folium.Element(ui))

#=====說明欄=====

info_html = """
<div id="info-panel">

<div id="info-tab">資料說明</div>

<div id="info-content">

<div class="info-title">
危害風險資料說明
</div>

<div class="info-section">

<b>資料來源</b><br>
本系統危害風險資料依據TCCIP提供之嘉義市最小統計區尺度之
AR6氣候情境推估成果建置，包含  1.5 °C、 2.0°C與4.0°C 情境，
以空間統計方式計算各區域風險分級。
其餘圖層資料皆於政府資料開放平台蒐集。
</div>

<div class="info-section">

<b>風險等級解釋</b>

<ul>
<li><b>1級（最低）</b>：低風險</li>
<li><b>2級</b>：中低風險</li>
<li><b>3級</b>：中風險</li>
<li><b>4級</b>：中高風險</li>
<li><b>5級（最高）</b>：高風險</li>
</ul>

</div>


</div>
</div>


<style>

#info-panel{
position:fixed;
left:20px;
bottom:20px;
width:380px;
z-index:10002;
font-family:Microsoft JhengHei;
transition:transform 0.35s ease;
transform:translateX(-360px);
}

#info-panel.open{
transform:translateX(0);
}

.case-box{
background:#f7f9fc;
padding:10px 12px;
border-radius:8px;
margin-top:10px;
border-left:4px solid #2c7be5;
}

#info-tab{
position:absolute;
right:-90px;
top:0;
width:90px;
height:42px;
background:#2c7be5;
color:white;
display:flex;
align-items:center;
justify-content:center;
cursor:pointer;
border-radius:0 8px 8px 0;
font-weight:bold;
box-shadow:0 4px 12px rgba(0,0,0,0.25);
}

#info-content{
background:rgba(255,255,255,0.96);
padding:18px;
border-radius:0 12px 12px 0;
box-shadow:0 6px 20px rgba(0,0,0,0.25);
max-height:520px;
overflow-y:auto;
}

.info-title{
font-size:17px;
font-weight:700;
margin-bottom:14px;
}

.info-section{
font-size:13px;
line-height:1.8;
margin-bottom:16px;
color:#333;
}

.info-section ul{
padding-left:18px;
margin-top:8px;
}

</style>

<script>

setTimeout(function(){

    let tab = document.getElementById("info-tab");

    if(tab){

        tab.onclick = function(){

            document
            .getElementById("info-panel")
            .classList.toggle("open");

        }

    }

},800);

</script>
"""



#=====圖層等級(圖例)=====
legend_html = """
<div id="legend-box" style="
position: fixed;
bottom: 20px;
right: 20px;
z-index: 10001;
background: white;
padding: 14px;
border-radius: 10px;
box-shadow: 0 4px 15px rgba(0,0,0,0.2);
font-family: Microsoft JhengHei;
width: 180px;
">

<div style="font-size:15px;font-weight:bold;margin-bottom:10px;">
AR6之淹水風險
</div>

<div style="font-size:13px;line-height:1.9;">
<div><span style="display:inline-block;width:16px;height:16px;background:#FEF87B;margin-right:6px;"></span>1級:低風險</div>
<div><span style="display:inline-block;width:16px;height:16px;background:#FECE7C;margin-right:6px;"></span>2級:中低風險</div>
<div><span style="display:inline-block;width:16px;height:16px;background:#FDA07B;margin-right:6px;"></span>3級:中風險</div>
<div><span style="display:inline-block;width:16px;height:16px;background:#FD7B7B;margin-right:6px;"></span>4級:中高風險</div>
<div><span style="display:inline-block;width:16px;height:16px;background:#C47B7B;margin-right:6px;"></span>5級:高風險</div>
</div>

</div>
"""

# ==========================================
# 8. 輸出
# ==========================================
m.get_root().html.add_child(folium.Element(legend_html))
m.get_root().html.add_child(folium.Element(info_html))

m.save(str(OUTPUT_HTML))

print("完成輸出：", OUTPUT_HTML)