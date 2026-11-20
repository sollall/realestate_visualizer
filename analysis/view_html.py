"""物件からの眺め(一人称視点)をdeck.glで描画するHTMLを組み立てる。

Streamlit標準の`st.pydeck_chart`は`views`の指定を無視して常に地図を見下ろす
MapViewで描画するため、一人称視点(FirstPersonView)が使えない。そこでdeck.glを
直接読み込む単体のHTMLを作り、`streamlit.components.v1.html`で埋め込む。
"""

import json

DECK_GL_URL = "https://unpkg.com/deck.gl@9.1.14/dist.min.js"

_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<script src="__DECK_GL_URL__"></script>
<style>
  html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; font-family: sans-serif; }
  #container {
    position: relative; width: 100%; height: 100%;
    /* deck.glのキャンバスは透過なので、背景をそのまま空として見せる */
    background: linear-gradient(to bottom, #6fa8dc 0%, #b7d3ee 55%, #e4eef7 100%);
  }
  #hud {
    position: absolute; left: 10px; top: 10px; z-index: 2;
    background: rgba(0, 0, 0, 0.55); color: #fff; padding: 8px 10px;
    border-radius: 6px; font-size: 12px; line-height: 1.6; pointer-events: none;
  }
  #hud b { font-size: 14px; }
  #buttons { position: absolute; right: 10px; top: 10px; z-index: 2; display: flex; gap: 4px; }
  #buttons button {
    background: rgba(255, 255, 255, 0.9); border: 1px solid #888; border-radius: 4px;
    padding: 4px 8px; cursor: pointer; font-size: 12px;
  }
  #help {
    position: absolute; left: 10px; bottom: 10px; z-index: 2;
    background: rgba(255, 255, 255, 0.8); color: #333; padding: 4px 8px;
    border-radius: 4px; font-size: 11px; pointer-events: none;
  }
  #error { padding: 20px; color: #b00; }
</style>
</head>
<body>
<div id="container">
  <div id="hud"></div>
  <div id="buttons">
    <button data-bearing="0">北</button>
    <button data-bearing="90">東</button>
    <button data-bearing="180">南</button>
    <button data-bearing="270">西</button>
    <button id="reset">リセット</button>
  </div>
  <div id="help">ドラッグで見回し / 矢印キー・WASDで移動 / 建物にカーソルで高さ表示</div>
</div>
<script>
(function () {
  if (typeof deck === "undefined") {
    document.getElementById("container").innerHTML =
      '<div id="error">deck.glを読み込めませんでした(__DECK_GL_URL__ へのアクセスを確認してください)。</div>';
    return;
  }
  const config = __CONFIG__;
  const scene = config.scene;
  const DIRS = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東",
                "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"];

  const initialViewState = {
    longitude: config.lon,
    latitude: config.lat,
    position: [0, 0, config.eyeHeight],
    bearing: config.bearing,
    pitch: config.pitch,
    minPitch: -89,
    maxPitch: 89,
  };
  let viewState = Object.assign({}, initialViewState);

  // 建物の色: 高い建物ほど濃く。高さタグが無く推定した建物は灰色寄りにする
  function buildingColor(d) {
    const t = Math.min(1, d.height / 60);
    if (d.estimated) {
      return [215 - 40 * t, 210 - 40 * t, 200 - 40 * t, 255];
    }
    return [235 - 120 * t, 225 - 90 * t, 205 - 30 * t, 255];
  }

  // 地面系のレイヤーはすべてz=0に重なるため、深度を書き込まず描画順で重ねる
  const groundParams = { depthWriteEnabled: false, depthCompare: "always" };

  const layers = [
    new deck.SolidPolygonLayer({
      id: "ground",
      data: [{ polygon: config.groundPolygon }],
      getPolygon: (d) => d.polygon,
      getFillColor: [222, 218, 208],
      parameters: groundParams,
    }),
    new deck.SolidPolygonLayer({
      id: "green",
      data: scene.green,
      getPolygon: (d) => d.polygon,
      getFillColor: [170, 210, 150],
      parameters: groundParams,
    }),
    new deck.SolidPolygonLayer({
      id: "water",
      data: scene.water,
      getPolygon: (d) => d.polygon,
      getFillColor: [120, 170, 220],
      parameters: groundParams,
    }),
    new deck.PathLayer({
      id: "roads",
      data: scene.roads,
      getPath: (d) => d.path,
      getWidth: (d) => d.width,
      widthUnits: "meters",
      capRounded: true,
      jointRounded: true,
      getColor: [250, 250, 248],
      parameters: groundParams,
    }),
    new deck.PathLayer({
      id: "rails",
      data: scene.rails,
      getPath: (d) => d.path,
      getWidth: 3,
      widthUnits: "meters",
      getColor: [110, 110, 120],
      parameters: groundParams,
    }),
    new deck.PolygonLayer({
      id: "buildings",
      data: scene.buildings,
      // 下端の高さ(min_height)はポリゴンのz座標で、上端までの差を押し出しの高さで表す
      getPolygon: (d) => liftPolygon(d.polygon, d.base),
      extruded: true,
      wireframe: true,
      getElevation: (d) => d.height - d.base,
      getFillColor: buildingColor,
      getLineColor: [90, 90, 90, 160],
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 200, 0, 200],
      material: { ambient: 0.6, diffuse: 0.5, shininess: 8, specularColor: [40, 40, 40] },
    }),
  ];

  // OSMのタグ値は外部入力なので、tooltipのHTMLに入れる前にエスケープする
  function esc(text) {
    return String(text).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }

  function liftPolygon(polygon, z) {
    if (!z) return polygon;
    const lift = (ring) => ring.map((p) => [p[0], p[1], z]);
    return Array.isArray(polygon[0][0]) ? polygon.map(lift) : lift(polygon);
  }

  function updateHud(vs) {
    const bearing = ((vs.bearing % 360) + 360) % 360;
    const dir = DIRS[Math.round(bearing / 22.5) % 16];
    const height = vs.position ? vs.position[2] : config.eyeHeight;
    document.getElementById("hud").innerHTML =
      "<b>" + config.title + "</b><br>" +
      "向き: " + dir + " (" + bearing.toFixed(0) + "°)" +
      " / 見上げ角: " + vs.pitch.toFixed(0) + "°<br>" +
      "目線の高さ: 約" + height.toFixed(1) + "m";
  }

  const deckgl = new deck.Deck({
    parent: document.getElementById("container"),
    views: new deck.FirstPersonView({
      id: "first-person",
      fovy: 60,
      near: 0.5,
      far: 20000,
      controller: { keyboard: { moveSpeed: 5, rotateSpeedX: 5, rotateSpeedY: 5 }, dragMode: "rotate" },
    }),
    viewState: viewState,
    layers: layers,
    onViewStateChange: ({ viewState: vs }) => {
      viewState = vs;
      deckgl.setProps({ viewState: vs });
      updateHud(vs);
    },
    getTooltip: ({ object }) => {
      if (!object) return null;
      const name = object.name ? esc(object.name) + "<br>" : "";
      const levels = object.levels ? " (" + esc(object.levels) + "階建て)" : "";
      const note = object.estimated ? "<br><i>高さタグが無いため推定値</i>" : "";
      return { html: name + "高さ: " + object.height.toFixed(1) + "m" + levels + note };
    },
  });
  updateHud(viewState);

  function setView(patch) {
    viewState = Object.assign({}, viewState, patch);
    deckgl.setProps({ viewState: viewState });
    updateHud(viewState);
  }
  document.querySelectorAll("#buttons button[data-bearing]").forEach((btn) => {
    btn.addEventListener("click", () => setView({ bearing: Number(btn.dataset.bearing) }));
  });
  document.getElementById("reset").addEventListener("click", () => setView(initialViewState));
})();
</script>
</body>
</html>
"""


def build_view_html(scene, lon, lat, eye_height, bearing, pitch, ground_polygon, title="", deck_gl_url=DECK_GL_URL):
    """一人称視点で周辺を眺めるdeck.glのHTML文字列を返す。

    Args:
        scene: `analysis.osm_view.build_scene`の戻り値
        lon, lat: 視点(物件)の位置
        eye_height: 目線の高さ[m]
        bearing: 見る方角(北=0, 時計回り)[度]
        pitch: 見上げ角(水平=0, 上向きが正)[度]
        ground_polygon: 地面として敷く多角形([[lon, lat], ...])
        title: 画面左上に表示するタイトル
    """
    config = {
        "scene": scene,
        "lon": lon,
        "lat": lat,
        "eyeHeight": eye_height,
        "bearing": bearing,
        "pitch": pitch,
        "groundPolygon": ground_polygon,
        "title": _escape_html(title),
    }
    # 建物名などに"</script>"が含まれていてもscriptタグが閉じないようにする
    config_json = json.dumps(config, ensure_ascii=False).replace("</", "<\\/")
    return _TEMPLATE.replace("__DECK_GL_URL__", deck_gl_url).replace("__CONFIG__", config_json)


def _escape_html(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
