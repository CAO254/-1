<!-- [界面美化] 人工智能NLP-Agent数字人项目-教育智能体 —— 动态流动风景背景组件（纯CSS/SVG，零依赖零图片） -->
<template>
  <div class="scene" :class="variant">
    <div class="sky"></div>
    <div class="aurora a1"></div>
    <div class="aurora a2"></div>
    <div class="aurora a3"></div>

    <template v-if="variant === 'full'">
      <span
        v-for="s in stars" :key="'s' + s.id" class="star"
        :style="{ left: s.x + '%', top: s.y + '%', width: s.size + 'px', height: s.size + 'px', animationDelay: s.delay + 's', animationDuration: s.dur + 's' }"
      ></span>
      <div class="sun"></div>
      <div class="cloud c1"></div>
      <div class="cloud c2"></div>
      <div class="cloud c3"></div>

      <div class="mountains far"><div class="drift d1">
        <svg viewBox="0 0 1440 320" preserveAspectRatio="none"><path :d="farPath" /></svg>
        <svg viewBox="0 0 1440 320" preserveAspectRatio="none"><path :d="farPath" /></svg>
      </div></div>
      <div class="mountains mid"><div class="drift d2">
        <svg viewBox="0 0 1440 320" preserveAspectRatio="none"><path :d="midPath" /></svg>
        <svg viewBox="0 0 1440 320" preserveAspectRatio="none"><path :d="midPath" /></svg>
      </div></div>
      <div class="mountains near"><div class="drift d3">
        <svg viewBox="0 0 1440 320" preserveAspectRatio="none"><path :d="nearPath" /></svg>
        <svg viewBox="0 0 1440 320" preserveAspectRatio="none"><path :d="nearPath" /></svg>
      </div></div>

      <div class="water">
        <div class="glow-streak"></div>
        <div class="aurora-mirror"></div>
        <div class="waves w1"><div class="drift d4">
          <svg viewBox="0 0 1440 60" preserveAspectRatio="none"><path :d="wavePath" /></svg>
          <svg viewBox="0 0 1440 60" preserveAspectRatio="none"><path :d="wavePath" /></svg>
        </div></div>
        <div class="waves w2"><div class="drift d5">
          <svg viewBox="0 0 1440 60" preserveAspectRatio="none"><path :d="wavePath" /></svg>
          <svg viewBox="0 0 1440 60" preserveAspectRatio="none"><path :d="wavePath" /></svg>
        </div></div>
      </div>

      <span
        v-for="f in flies" :key="'f' + f.id" class="fly"
        :style="{ left: f.x + '%', bottom: f.y + 'px', width: f.size + 'px', height: f.size + 'px', animationDelay: f.delay + 's', animationDuration: f.dur + 's', '--dx': f.dx + 'px' }"
      ></span>
    </template>

    <div v-else class="veil"></div>
  </div>
</template>

<script setup>
defineProps({ variant: { type: String, default: 'full' } })

const rand = (min, max) => min + Math.random() * (max - min)

const stars = Array.from({ length: 40 }, (_, id) => ({
  id, x: rand(0, 100), y: rand(0, 30), size: rand(1, 2.2), delay: rand(0, 6), dur: rand(2.4, 6),
}))
const flies = Array.from({ length: 14 }, (_, id) => ({
  id, x: rand(4, 96), y: rand(30, 160), size: rand(3, 5.5), delay: rand(0, 8), dur: rand(7, 14), dx: rand(-50, 50),
}))

const farPath = 'M0 170 L110 150 L235 205 L360 118 L505 195 L640 132 L790 208 L930 145 L1075 200 L1210 138 L1330 196 L1440 170 L1440 320 L0 320 Z'
const midPath = 'M0 235 L130 175 L285 232 L430 150 L590 225 L750 160 L905 235 L1060 165 L1205 228 L1330 178 L1440 235 L1440 320 L0 320 Z'
const nearPath = 'M0 275 L165 205 L330 262 L505 178 L680 258 L860 190 L1035 265 L1210 200 L1440 275 L1440 320 L0 320 Z'
const wavePath = 'M0 30 C120 10 240 50 360 30 C480 10 600 50 720 30 C840 10 960 50 1080 30 C1200 10 1320 50 1440 30 L1440 60 L0 60 Z'
</script>

<style scoped>
.scene { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
.sky { position: absolute; inset: 0; background: linear-gradient(180deg, #1e2a52 0%, #4a3170 22%, #91497a 42%, #d4696a 58%, #f2955c 74%, #ffc46b 88%, #ffdf9e 100%); }

.aurora { position: absolute; border-radius: 50%; filter: blur(70px); mix-blend-mode: screen; opacity: 0.55; animation: hue 22s linear infinite, sway 14s ease-in-out infinite alternate; }
.a1 { width: 55vw; height: 34vh; left: -8vw; top: 4vh; background: linear-gradient(120deg, #ff9a8b, #ffb88c 70%); }
.a2 { width: 46vw; height: 30vh; right: -6vw; top: 14vh; background: linear-gradient(120deg, #ffd166, #ff8f6b 60%, #ffb3a7); opacity: 0.45; animation-duration: 26s, 18s; }
.a3 { width: 38vw; height: 24vh; left: 24vw; top: -4vh; background: linear-gradient(120deg, #b86bff, #ff7eb3); opacity: 0.32; animation-duration: 30s, 12s; }
@keyframes hue { 0%, 100% { filter: blur(70px) hue-rotate(0deg); } 50% { filter: blur(70px) hue-rotate(28deg); } }
@keyframes sway { from { transform: translate3d(-3vw, 1vh, 0) rotate(-14deg); } to { transform: translate3d(3vw, -2vh, 0) rotate(-10deg); } }

.star { position: absolute; border-radius: 50%; background: #fff; box-shadow: 0 0 6px rgba(255, 244, 214, 0.8); opacity: 0.2; animation: twinkle linear infinite; }
@keyframes twinkle { 0%, 100% { opacity: 0.1; transform: scale(0.8); } 50% { opacity: 0.7; transform: scale(1.15); } }

.sun { position: absolute; right: 15vw; top: 54%; width: 74px; height: 74px; border-radius: 50%; background: radial-gradient(circle at 42% 42%, #fffbe8, #ffe1a0 55%, #ffb84d); box-shadow: 0 0 50px 18px rgba(255, 180, 90, 0.55), 0 0 140px 60px rgba(255, 140, 100, 0.28); animation: sunBreath 8s ease-in-out infinite; }
@keyframes sunBreath { 0%, 100% { transform: scale(1); box-shadow: 0 0 50px 18px rgba(255, 180, 90, 0.55), 0 0 140px 60px rgba(255, 140, 100, 0.28); } 50% { transform: scale(1.05); box-shadow: 0 0 64px 24px rgba(255, 190, 100, 0.65), 0 0 160px 70px rgba(255, 150, 110, 0.34); } }

.cloud { position: absolute; left: 0; border-radius: 50%; background: rgba(255, 205, 160, 0.16); filter: blur(26px); animation: cloudA linear infinite; }
.c1 { width: 340px; height: 110px; top: 18%; animation-duration: 95s; }
.c2 { width: 260px; height: 90px; top: 32%; animation-duration: 70s; animation-delay: -30s; }
.c3 { width: 420px; height: 130px; top: 8%; animation-duration: 120s; animation-delay: -70s; }
@keyframes cloudA { from { transform: translateX(-40vw); } to { transform: translateX(120vw); } }

.mountains { position: absolute; left: 0; width: 100%; }
.mountains.far { bottom: 20%; height: 36vh; }
.mountains.mid { bottom: 18%; height: 30vh; }
.mountains.near { bottom: 16%; height: 26vh; }
.far path { fill: #b06a72; opacity: 0.82; }
.mid path { fill: #6f3752; }
.near path { fill: #46223d; }
.drift { display: flex; width: 200%; height: 100%; animation: drift linear infinite; }
.drift svg { flex: none; width: 50%; height: 100%; }
.d1 { animation-duration: 140s; }
.d2 { animation-duration: 100s; }
.d3 { animation-duration: 70s; }
.d4 { animation-duration: 22s; }
.d5 { animation-duration: 30s; animation-direction: reverse; }
@keyframes drift { to { transform: translateX(-50%); } }

.water { position: absolute; left: 0; right: 0; bottom: 0; height: 24%; overflow: hidden; background: linear-gradient(180deg, #ef9a5e 0%, #c05c4f 45%, #5c2b47 100%); }
.glow-streak { position: absolute; right: calc(15vw + 26px); top: -6%; height: 120%; width: 84px; background: linear-gradient(180deg, rgba(255, 218, 140, 0.62), rgba(255, 196, 120, 0.14) 70%, transparent); filter: blur(11px); animation: shimmer 6s ease-in-out infinite; }
@keyframes shimmer { 0%, 100% { opacity: 0.55; transform: scaleY(1); } 50% { opacity: 0.95; transform: scaleY(1.06); } }
.aurora-mirror { position: absolute; left: 6vw; right: 22vw; top: 8%; height: 46%; background: linear-gradient(90deg, rgba(255, 150, 110, 0.3), rgba(255, 214, 130, 0.26), rgba(255, 122, 152, 0.18)); filter: blur(24px); animation: hue 22s linear infinite; }
.waves { position: absolute; left: 0; width: 100%; height: 38px; }
.w1 { top: -16px; opacity: 0.5; }
.w2 { top: -8px; opacity: 0.35; }
.w1 path { fill: rgba(255, 208, 158, 0.2); }
.w2 path { fill: rgba(255, 160, 120, 0.18); }

.fly { position: absolute; border-radius: 50%; background: radial-gradient(circle, #fff3c4, #ffc94d 60%, transparent); box-shadow: 0 0 10px 3px rgba(255, 200, 90, 0.5); opacity: 0; animation: floatUp ease-in-out infinite; }
@keyframes floatUp { 0% { opacity: 0; transform: translate(0, 0) scale(0.7); } 15% { opacity: 0.9; } 60% { opacity: 0.7; } 100% { opacity: 0; transform: translate(var(--dx, 0), -120px) scale(1.1); } }

.veil { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(255, 250, 244, 0.82), rgba(255, 243, 233, 0.9)); }
.scene.soft .sky { background: linear-gradient(160deg, #fff4e6 0%, #ffe9ec 45%, #fdf3e0 100%); }
.scene.soft .aurora { mix-blend-mode: normal; opacity: 0.5; }
.scene.soft .a1 { opacity: 0.4; }
.scene.soft .a2 { opacity: 0.3; }
.scene.soft .a3 { opacity: 0.24; }

@media (prefers-reduced-motion: reduce) {
  .scene *, .scene { animation: none !important; }
}
</style>
