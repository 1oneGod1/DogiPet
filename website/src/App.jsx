import { useEffect, useState } from "react";
import {
  Bone,
  CalendarDots,
  Check,
  DownloadSimple,
  GithubLogo,
  House,
  Keyboard,
  List,
  LockKey,
  Monitor,
  NotePencil,
  ShieldCheck,
  Sparkle,
  UsersThree,
  VideoCamera,
  WindowsLogo,
  X,
} from "@phosphor-icons/react";

const DOWNLOAD_URL =
  "https://github.com/1oneGod1/DogiPet/releases/download/continuous/DogiPet-Setup.exe";
const REPO_URL = "https://github.com/1oneGod1/DogiPet";
const ASSET_URL = `${import.meta.env.BASE_URL}assets/`;

const heroModes = [
  {
    id: "desktop",
    label: "Desktop",
    Icon: Monitor,
    frames: ["walk_0.png", "walk_1.png", "walk_2.png", "walk_3.png"],
    message: "Aku bisa jalan lintas monitor!",
  },
  {
    id: "work",
    label: "Mengetik",
    Icon: Keyboard,
    frames: ["type_0.png", "type_4.png", "type_8.png", "type_12.png"],
    message: "Makin lama mengetik, makin panas.",
  },
  {
    id: "meeting",
    label: "Rapat",
    Icon: VideoCamera,
    frames: ["meeting_alert_0.png", "meeting_watch_0.png"],
    message: "Ada orang asing di layar? Gong!",
  },
  {
    id: "play",
    label: "Bermain",
    Icon: Bone,
    frames: ["fetch_0.png", "friend_play_0.png", "friend_tussle_0.png"],
    message: "Lempar mainan, Dogi akan mengejar.",
  },
];

const features = [
  {
    number: "01",
    title: "JALAN DI BANYAK LAYAR",
    description: "Dogi berjalan horizontal dan vertikal, bahkan ke monitor lain.",
    Icon: Monitor,
    sprites: ["walk_0.png", "walk_2.png"],
  },
  {
    number: "02",
    title: "KERJA SAMPAI PANAS",
    description: "Keyboard lengkap, kaki bergerak, muka memerah, lalu muncul asap.",
    Icon: Keyboard,
    sprites: ["type_0.png", "type_12.png"],
  },
  {
    number: "03",
    title: "GONGGONG SAAT RAPAT",
    description: "Dogi melihat ke layar meeting, berjaga, dan menggonggong sekali.",
    Icon: VideoCamera,
    sprites: ["meeting_alert_0.png"],
  },
  {
    number: "04",
    title: "SERET MAKANAN & MAINAN",
    description: "Tulang, bola, frisbee, tali, kasur, dan rumah bebas dipindahkan.",
    Icon: Bone,
    sprites: ["wait_food_0.png", "fetch_0.png"],
  },
  {
    number: "05",
    title: "BERMAIN & BERSOSIAL",
    description: "Sampai empat Dogi dapat bermain, mengejar, berpelukan, dan adu lucu.",
    Icon: UsersThree,
    sprites: ["friend_play_0.png", "friend_tussle_0.png"],
  },
  {
    number: "06",
    title: "CATATAN & KALENDER",
    description: "Daily Hub merangkum tugas, catatan, notulen, dan agenda Google Calendar.",
    Icon: CalendarDots,
    sprites: ["happy_0.png"],
  },
];

const faqs = [
  ["Apakah DogiPet gratis?", "Ya. Installer continuous tersedia langsung dari GitHub Releases."],
  ["Apakah Dogi merekam saya?", "Tidak otomatis. Rekaman rapat dan reaksi suara hanya aktif setelah Anda menyalakannya."],
  ["Apakah AI membaca semua data?", "Tidak. Tanya Dogi hanya menerima sumber yang Anda pilih secara eksplisit."],
];

function PixelSprite({ frames, className = "", alt = "Dogi pixel" }) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
    if (frames.length < 2) return undefined;
    const timer = window.setInterval(
      () => setIndex((value) => (value + 1) % frames.length),
      260,
    );
    return () => window.clearInterval(timer);
  }, [frames]);

  return (
    <img
      className={`pixel-sprite ${className}`}
      src={`${ASSET_URL}${frames[index]}`}
      alt={alt}
      draggable="false"
    />
  );
}

function DownloadButton({ compact = false, dark = false }) {
  return (
    <a
      className={`download-button${compact ? " download-button--compact" : ""}${dark ? " download-button--dark" : ""}`}
      href={DOWNLOAD_URL}
      aria-label="Unduh installer DogiPet untuk Windows"
    >
      <DownloadSimple size={compact ? 18 : 24} weight="bold" />
      <span>{compact ? "UNDUH" : "UNDUH DOGIPET SEKARANG"}</span>
    </a>
  );
}

function Header() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <header className="site-header">
      <a className="brand" href="#top" aria-label="DogiPet beranda" onClick={close}>
        <img src={`${ASSET_URL}idle_0.png`} alt="" />
        <span>DOGIPET</span>
      </a>
      <button
        className="menu-button"
        type="button"
        aria-label={open ? "Tutup menu" : "Buka menu"}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? <X size={24} /> : <List size={24} />}
      </button>
      <nav className={open ? "nav nav--open" : "nav"} aria-label="Navigasi utama">
        <a href="#world" onClick={close}>DUNIA DOGI</a>
        <a href="#features" onClick={close}>FITUR</a>
        <a href="#download" onClick={close}>UNDUH</a>
        <a href="#faq" onClick={close}>FAQ</a>
      </nav>
      <a className="version-badge" href={REPO_URL} target="_blank" rel="noreferrer">
        VERSI 2.1.0
      </a>
    </header>
  );
}

function Hero() {
  const [mode, setMode] = useState(heroModes[0]);

  return (
    <section className="hero" id="world">
      <div className="hero-copy">
        <p className="eyebrow">TEMAN DESKTOP WINDOWS</p>
        <h1>KECIL DI LAYAR.<br /><span>BESAR TINGKAHNYA.</span></h1>
        <p className="hero-lead">
          Dogi hidup di desktopmu. Ia berjalan, bermain, belajar trik, menemani
          kerja, merapikan catatan, dan mengingat agenda—tanpa mengambil alih layarmu.
        </p>
        <div className="hero-stats" aria-label="Ringkasan DogiPet">
          <span><UsersThree size={23} weight="fill" /><b>4</b> DOGI</span>
          <span><Sparkle size={23} weight="fill" /><b>6</b> TRIK</span>
          <span><NotePencil size={23} weight="fill" /><b>200</b> MOMEN</span>
          <span><ShieldCheck size={23} weight="fill" /> AI DENGAN IZINMU</span>
        </div>
      </div>

      <div className="hero-stage">
        <div className="desktop-window" aria-label="Pratinjau DogiPet di desktop Windows">
          <div className="window-bar">
            <span><WindowsLogo weight="fill" /> DESKTOP DOGI</span>
            <span className="window-actions">— □ ×</span>
          </div>
          <div className="desktop-scene">
            <div className="monitor-row" aria-hidden="true">
              <Monitor size={76} weight="duotone" />
              <Monitor size={76} weight="duotone" />
              <Monitor size={76} weight="duotone" />
            </div>
            <p className="speech-bubble">{mode.message}</p>
            <PixelSprite frames={mode.frames} className="hero-dogi" />
            <div className="desktop-object" aria-hidden="true">
              {mode.id === "play" ? <Bone size={38} weight="fill" /> : <House size={38} weight="duotone" />}
            </div>
          </div>
          <div className="mode-tabs">
            {heroModes.map((item) => (
              <button
                type="button"
                key={item.id}
                className={item.id === mode.id ? "mode-tab mode-tab--active" : "mode-tab"}
                onClick={() => setMode(item)}
              >
                <item.Icon size={18} weight="bold" />
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        </div>

        <aside className="download-ticket" id="download">
          <p>PASANG GRATIS</p>
          <h2>DogiPet<br />untuk Windows</h2>
          <DownloadButton dark />
          <dl>
            <div><dt>SISTEM</dt><dd>Windows 10/11</dd></div>
            <div><dt>VERSI</dt><dd>2.1.0 (64-bit)</dd></div>
            <div><dt>UPDATE</dt><dd>Otomatis dari GitHub</dd></div>
          </dl>
        </aside>
      </div>

      <div className="capability-strip">
        <div><Monitor size={31} /><span><b>TINGGAL</b> di desktopmu</span></div>
        <div><Keyboard size={31} /><span><b>KERJA</b> sambil menemani</span></div>
        <div><VideoCamera size={31} /><span><b>RAPAT</b> tanpa mengganggu</span></div>
        <div><Bone size={31} /><span><b>MAIN</b> atau kasih makan</span></div>
        <div><UsersThree size={31} /><span><b>TEMAN</b> dan interaksi</span></div>
        <div><CalendarDots size={31} /><span><b>AGENDA</b> dan catatan</span></div>
      </div>
    </section>
  );
}

function FeatureCard({ feature }) {
  return (
    <article className="feature-card">
      <div className="feature-heading">
        <span className="feature-number">{feature.number}</span>
        <h3>{feature.title}</h3>
        <feature.Icon size={22} weight="bold" />
      </div>
      <div className="feature-visual">
        {feature.sprites.map((sprite, index) => (
          <img key={sprite} src={`${ASSET_URL}${sprite}`} alt="" className={`feature-dogi feature-dogi--${index + 1}`} />
        ))}
        <feature.Icon className="feature-ghost-icon" size={74} weight="duotone" />
      </div>
      <p>{feature.description}</p>
    </article>
  );
}

function AiSection() {
  return (
    <section className="ai-section" id="privacy">
      <div className="section-title-row">
        <h2>AI DENGAN IZINMU</h2>
        <Sparkle size={30} weight="fill" />
      </div>
      <div className="ai-flow">
        <div><NotePencil size={35} /><b>KAMU MEMILIH</b><span>Catatan, tugas, atau transkrip.</span></div>
        <span className="flow-arrow">→</span>
        <div><Sparkle size={35} /><b>DOGI MEMBANTU</b><span>Rapikan, ringkas, atau tanya Codex.</span></div>
        <span className="flow-arrow">→</span>
        <div><LockKey size={35} /><b>DATA TERJAGA</b><span>Sandbox baca-saja dan sumber terbatas.</span></div>
        <span className="flow-arrow">→</span>
        <div><ShieldCheck size={35} /><b>IZIN UTAMA</b><span>Tidak ada aksi otomatis tanpa kamu.</span></div>
      </div>
      <p className="privacy-note">Tidak ada data yang dikirim ke AI tanpa pilihan dan tindakanmu.</p>
    </section>
  );
}

function Faq() {
  return (
    <section className="faq-section" id="faq">
      <div className="section-title-row"><h2>PERTANYAAN SINGKAT</h2></div>
      <div className="faq-list">
        {faqs.map(([question, answer]) => (
          <details key={question}>
            <summary>{question}<span>+</span></summary>
            <p>{answer}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

export function App() {
  const qaMode = new URLSearchParams(window.location.search).get("qa") === "1";
  return (
    <div className={qaMode ? "site-shell qa-mode" : "site-shell"} id="top">
      <Header />
      <main>
        <Hero />
        <section className="features-section" id="features">
          <div className="section-title-row">
            <h2>TINGKAH DOGIPET</h2>
            <span>06 FITUR PILIHAN</span>
          </div>
          <div className="features-grid">
            {features.map((feature) => <FeatureCard key={feature.number} feature={feature} />)}
          </div>
        </section>
        <AiSection />
        <Faq />
        <section className="final-cta">
          <PixelSprite frames={["idle_0.png", "idle_1.png"]} />
          <div>
            <p>TEMAN DESKTOP</p>
            <h2>YANG BENAR-BENAR HIDUP.</h2>
          </div>
          <DownloadButton />
        </section>
      </main>
      <footer>
        <a className="brand" href="#top"><img src={`${ASSET_URL}idle_0.png`} alt="" /><span>DOGIPET</span></a>
        <p>© 2026 DogiPet. Dibuat untuk menemani setiap hari.</p>
        <a href={REPO_URL} target="_blank" rel="noreferrer"><GithubLogo size={22} weight="fill" /> GITHUB</a>
      </footer>
      <div className="sticky-download">
        <span><img src={`${ASSET_URL}idle_0.png`} alt="" /><b>DOGIPET 2.1</b></span>
        <DownloadButton compact />
      </div>
    </div>
  );
}
