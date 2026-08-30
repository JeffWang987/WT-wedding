const eventDate = new Date("2026-09-12T15:38:00+08:00");
const countdown = document.querySelector("#countdown");
const countdownNote = document.querySelector("#countdownNote");

function updateCountdown() {
  const difference = eventDate.getTime() - Date.now();
  const safeDifference = Math.max(0, difference);
  const totalSeconds = Math.floor(safeDifference / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const values = { days, hours, minutes, seconds };
  Object.entries(values).forEach(([unit, value]) => {
    const node = countdown?.querySelector(`[data-unit="${unit}"]`);
    if (node) node.textContent = String(value).padStart(2, "0");
  });
  if (difference <= 0 && countdownNote) countdownNote.textContent = "今天见 · 15:38 草坪仪式";
}
updateCountdown();
setInterval(updateCountdown, 1000);

const weatherCodeMap = {
  0: ["晴", "○"], 1: ["大部晴朗", "◔"], 2: ["多云", "◒"], 3: ["阴", "●"],
  45: ["有雾", "≋"], 48: ["雾凇", "≋"], 51: ["小毛毛雨", "╱"], 53: ["毛毛雨", "╱"], 55: ["毛毛雨", "╱"],
  61: ["小雨", "╱"], 63: ["中雨", "╱"], 65: ["大雨", "╱"], 71: ["小雪", "*"], 73: ["中雪", "*"], 75: ["大雪", "*"],
  80: ["阵雨", "╱"], 81: ["阵雨", "╱"], 82: ["强阵雨", "╱"], 95: ["雷雨", "ϟ"], 96: ["雷雨伴冰雹", "ϟ"], 99: ["雷雨伴冰雹", "ϟ"]
};
const weatherUrl = "https://api.open-meteo.com/v1/forecast?latitude=32.059&longitude=118.842&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia%2FShanghai&start_date=2026-09-11&end_date=2026-09-13";
const weatherDays = document.querySelector("#weatherDays");
const weatherStatus = document.querySelector("#weatherStatus");
const weatherSource = document.querySelector("#weatherSource");

function formatWeatherDate(isoDate, index) {
  const date = new Date(`${isoDate}T00:00:00+08:00`);
  const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
  return `${date.getMonth() + 1}.${String(date.getDate()).padStart(2, "0")} ${weekdays[date.getDay()]}`;
}

function renderWeather(data) {
  if (!weatherDays || !data?.daily?.time) return;
  const daily = data.daily;
  weatherDays.innerHTML = daily.time.map((date, index) => {
    const [description, icon] = weatherCodeMap[daily.weather_code[index]] || ["天气待定", "·"];
    const rain = daily.precipitation_probability_max?.[index];
    return `<article class="weather-day"><div class="weather-date">${formatWeatherDate(date, index)}</div><div class="weather-icon" aria-hidden="true">${icon}</div><div class="weather-desc">${description}</div><div class="weather-temp">${Math.round(daily.temperature_2m_max[index])}° <span>/ ${Math.round(daily.temperature_2m_min[index])}°</span></div><div class="weather-rain">降雨概率 ${rain ?? "-"}%</div></article>`;
  }).join("");
  weatherStatus?.classList.add("is-ready");
  if (weatherStatus) weatherStatus.innerHTML = '<span class="status-dot"></span> 预报已更新';
  if (weatherSource) weatherSource.textContent = "数据每次打开自动更新 · Open-Meteo · 南京紫金山庄附近";
}

async function loadWeather() {
  try {
    const response = await fetch(weatherUrl, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("weather request failed");
    renderWeather(await response.json());
  } catch (error) {
    if (weatherStatus) {
      weatherStatus.classList.add("is-error");
      weatherStatus.innerHTML = '<span class="status-dot"></span> 天气暂时无法更新';
    }
    if (weatherDays) weatherDays.innerHTML = '<div class="weather-empty">出发前请重新打开页面查看最新预报。</div>';
    if (weatherSource) weatherSource.textContent = "网络不可用时，天气模块会保留提示，不影响其他指南内容";
  }
}
loadWeather();

const bgm = document.querySelector("#bgm");
const musicToggle = document.querySelector("#musicToggle");
function setMusicUi(isPlaying) {
  if (!musicToggle) return;
  musicToggle.classList.toggle("is-playing", isPlaying);
  musicToggle.setAttribute("aria-pressed", String(isPlaying));
  musicToggle.setAttribute("aria-label", isPlaying ? "暂停背景音乐" : "播放背景音乐");
  const label = musicToggle.querySelector(".music-label");
  if (label) label.textContent = isPlaying ? "暂停音乐" : "播放音乐";
}

async function startMusic() {
  if (!bgm) return;
  try {
    await bgm.play();
    setMusicUi(true);
  } catch (error) {
    // Browsers may defer sound until the first user gesture.
    const resume = async (event) => {
      if (event?.target?.closest?.("#musicToggle")) return;
      try { await bgm.play(); setMusicUi(true); } catch (retryError) { return; }
    };
    document.addEventListener("pointerdown", resume, { once: true, passive: true });
    document.addEventListener("keydown", resume, { once: true });
  }
}
startMusic();
musicToggle?.addEventListener("click", async () => {
  if (!bgm) return;
  if (bgm.paused) {
    try { await bgm.play(); setMusicUi(true); } catch (error) { showToast("请再次点击播放音乐"); return; }
  } else {
    bgm.pause();
    setMusicUi(false);
  }
});

function showToast(message) {
  const toast = document.querySelector("#toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("is-visible"), 2200);
}

document.querySelector("#copyAddress")?.addEventListener("click", async () => {
  const address = "江苏省南京市玄武区环绕陵路18号";
  try {
    await navigator.clipboard.writeText(address);
    showToast("地址已复制");
  } catch (error) {
    showToast(address);
  }
});

const mapModal = document.querySelector("#mapModal");
const mapOpen = document.querySelector("#mapOpen");
const mapClose = document.querySelector("#mapClose");
function closeMap() { if (mapModal) mapModal.hidden = true; document.body.style.overflow = ""; }
mapOpen?.addEventListener("click", () => { if (mapModal) mapModal.hidden = false; document.body.style.overflow = "hidden"; });
mapClose?.addEventListener("click", closeMap);
mapModal?.addEventListener("click", (event) => { if (event.target === mapModal) closeMap(); });
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeMap(); });

document.querySelectorAll("img").forEach((image) => {
  if (image.complete && image.naturalWidth === 0) image.closest(".hero-photo, .cover-image, .map-frame, .map-modal, .memory-track figure")?.classList.add("asset-missing");
  image.addEventListener("error", () => image.closest(".hero-photo, .cover-image, .map-frame, .map-modal, .memory-track figure")?.classList.add("asset-missing"));
});
