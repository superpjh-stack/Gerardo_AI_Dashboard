import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  Box,
  Check,
  CheckCheck,
  ChevronRight,
  CircleHelp,
  Clock3,
  Code2,
  Database,
  FlaskConical,
  FolderOpen,
  Gauge,
  LayoutDashboard,
  Link2,
  LoaderCircle,
  Menu,
  MessageSquare,
  MoreHorizontal,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
  Unplug,
  X,
  Zap,
} from "lucide-react";
import type {
  Detail,
  Overview,
  Point,
  Provider,
  Source,
  Task,
  Tool,
} from "./types";
import { api } from "./api";

const names: Record<Provider, string> = {
  claude: "Claude",
  codex: "Codex",
  antigravity: "Antigravity",
};
const colors: Record<Provider, string> = {
  claude: "#f2b08d",
  codex: "#79d9bc",
  antigravity: "#b8a0f5",
};
const providers = Object.keys(names) as Provider[];
const compact = (n: number | null) =>
  n === null
    ? "미수집"
    : new Intl.NumberFormat("en", {
        notation: "compact",
        maximumFractionDigits: 1,
      }).format(n);
const integer = (n: number | null) =>
  n === null ? "미수집" : n.toLocaleString("ko-KR");
const date = (s: string | null) =>
  s
    ? new Intl.DateTimeFormat("ko-KR", {
        timeZone: "Asia/Seoul",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).format(new Date(s))
    : "기록 없음";
const time = (s: string) =>
  new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(s));
const stateName = (s: string) =>
  ({
    connected: "수집 연결됨",
    partial: "부분 수집",
    not_connected: "연결 준비",
    unavailable: "연결 미확인",
    error: "수집 오류",
    demo: "예시 데이터",
  })[s] || s;
const navigation = [
  { path: "/", label: "대시보드", shortLabel: "홈", icon: LayoutDashboard },
  { path: "/activity", label: "활동 타임라인", shortLabel: "활동", icon: Activity },
  { path: "/projects", label: "프로젝트", shortLabel: "프로젝트", icon: FolderOpen },
  { path: "/usage", label: "토큰 분석", shortLabel: "토큰", icon: Gauge },
  { path: "/sources", label: "데이터 소스", shortLabel: "소스", icon: Database },
];

function Mark({ provider, size = "" }: { provider: Provider; size?: string }) {
  const Icon =
    provider === "claude" ? Sparkles : provider === "codex" ? Code2 : Box;
  return (
    <span className={`tool-mark ${provider} ${size}`}>
      <Icon size={size === "small" ? 15 : 25} strokeWidth={1.7} />
    </span>
  );
}
function Empty({
  title = "이 기간에 수집된 활동이 없습니다.",
  body = "조회 기간을 바꾸거나 데이터 소스를 연결해 주세요.",
  action,
}: {
  title?: string;
  body?: string;
  action?: () => void;
}) {
  return (
    <div className="empty">
      <Activity size={28} />
      <strong>{title}</strong>
      <p>{body}</p>
      {action && (
        <button className="button" onClick={action}>
          데이터 소스 연결 <ArrowRight size={14} />
        </button>
      )}
    </div>
  );
}
function Chart({
  points,
  extended = false,
}: {
  points: Point[];
  extended?: boolean;
}) {
  const max = Math.max(
    1,
    ...points.map((p) => providers.reduce((s, k) => s + (p[k] || 0), 0)),
  );
  const has = points.some((p) => providers.some((k) => p[k] !== null));
  return (
    <div className="usage-chart">
      {has ? (
        <>
          <div className="chart-scroll" role="region" aria-label="일별 토큰 차트, 좌우로 스크롤" tabIndex={0}>
          <div className="chart-body" style={{ minWidth: points.length > 10 ? `${points.length * 30 + 48}px` : undefined }}>
            <div className="y-axis">
              <span>{compact(max)}</span>
              <span>{compact(Math.round(max / 2))}</span>
              <span>0</span>
            </div>
            <div className="plot">
              <div className="grid-line first" />
              <div className="grid-line second" />
              <div className="grid-line third" />
              <div className="bars">
                {points.map((p, i) => (
                  <div className="bar-column" key={p.date}>
                    <div
                      className="bar-stack"
                      tabIndex={0}
                      role="img"
                      aria-label={`${p.date}: ${providers.map((k) => `${names[k]} ${integer(p[k])}`).join(", ")}`}
                      title={`${p.date}\n${providers.map((k) => `${names[k]} ${integer(p[k])}`).join("\n")}`}
                    >
                      {providers.map((k) => (
                        <div
                          key={k}
                          className={`bar ${k}`}
                          style={{ height: `${((p[k] || 0) / max) * 100}%` }}
                        />
                      ))}
                    </div>
                    <span className="x-label">
                      {points.length <= 10 ||
                      i % Math.ceil(points.length / 8) === 0
                        ? p.date.slice(5).replace("-", ".")
                        : " "}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          </div>
          {points.length > 10 && <p className="chart-hint">차트를 좌우로 밀어 전체 기간을 확인하세요.</p>}
          <div className="chart-foot">
            <span>한국시간 기준 · 수집된 사용량</span>
            <div className="legend">
              {providers.map((k) => (
                <span key={k}>
                  <i style={{ background: colors[k] }} />
                  {names[k]}
                </span>
              ))}
            </div>
          </div>
        </>
      ) : (
        <Empty
          title="아직 그릴 사용량이 없습니다."
          body="토큰이 확인된 기록부터 차트에 표시됩니다."
        />
      )}
      <details className="chart-table" open={extended}>
        <summary>
          일별 수치 보기 <ChevronRight size={13} />
        </summary>
        <div className="table-scroll" role="region" aria-label="일별 토큰 수치, 좌우로 스크롤" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th>날짜</th>
                {providers.map((k) => (
                  <th key={k}>{names[k]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {points.map((p) => (
                <tr key={p.date}>
                  <td>{p.date}</td>
                  {providers.map((k) => (
                    <td key={k}>{integer(p[k])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
function ToolCard({ tool, onClick }: { tool: Tool; onClick: () => void }) {
  return (
    <button className={`tool-card ${tool.id}`} onClick={onClick}>
      <div className="tool-top">
        <div className="tool-name">
          <Mark provider={tool.id} />
          <div>
            <h3>{tool.name}</h3>
            <span>{tool.models[0] || "모델 미확인"}</span>
          </div>
        </div>
        <ChevronRight size={16} />
      </div>
      <div className={`status ${tool.source.status}`}>
        <i />
        {stateName(tool.source.status)}
      </div>
      <div className="tool-metrics">
        <div>
          <span>수집된 토큰</span>
          <strong>{compact(tool.usage.total_tokens)}</strong>
        </div>
        <div>
          <span>작업 세션</span>
          <strong>
            {tool.sessions}
            <small>개</small>
          </strong>
        </div>
      </div>
      <div className="tool-bottom">
        <Clock3 size={12} />
        <span>
          {tool.latest
            ? `최근 활동 ${date(tool.latest)}`
            : "아직 확인된 활동이 없습니다"}
        </span>
      </div>
    </button>
  );
}
function TaskRows({
  tasks,
  onSelect,
  limit = 6,
}: {
  tasks: Task[];
  onSelect: (task: Task) => void;
  limit?: number;
}) {
  return (
    <div className="task-list">
      {tasks.slice(0, limit).map((task) => (
        <button
          className="task-row"
          key={task.id}
          onClick={() => onSelect(task)}
        >
          <span className="task-clock">
            {time(task.occurred_at)}
            <small>
              {new Date(task.occurred_at).toLocaleDateString("ko-KR", {
                timeZone: "Asia/Seoul",
                month: "2-digit",
                day: "2-digit",
              })}
            </small>
          </span>
          <Mark provider={task.provider} size="small" />
          <div className="task-content">
            <strong>{task.project}</strong>
            <span>{task.summary}</span>
          </div>
          <div className="task-meta">
            <strong>
              {compact(task.usage.total_tokens)}
              <small> tokens</small>
            </strong>
            <span
              className={task.status === "user_confirmed" ? "confirmed" : ""}
            >
              {task.status === "user_confirmed" ? (
                <>
                  <Check size={11} /> 확인 완료
                </>
              ) : (
                names[task.provider]
              )}
            </span>
          </div>
          <ChevronRight className="row-chevron" size={14} />
        </button>
      ))}
    </div>
  );
}
function SessionDialog({
  task,
  demo,
  onClose,
  onUpdate,
}: {
  task: Task;
  demo: boolean;
  onClose: () => void;
  onUpdate: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [detail, setDetail] = useState<Detail | null>(null),
    [note, setNote] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const load = useCallback(
    () =>
      api<Detail>(`/tasks/${task.id}?demo=${demo}`)
        .then(setDetail)
        .catch((e) => setError(e.message)),
    [task.id, demo],
  );
  useEffect(() => {
    ref.current?.showModal();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    load();
    return () => { document.body.style.overflow = previousOverflow; };
  }, [load]);
  async function save(confirm = false) {
    setBusy(true);
    setError("");
    try {
      await api(`/tasks/${task.id}/${confirm ? "confirmations" : "notes"}`, {
        method: "POST",
        body: confirm ? undefined : JSON.stringify({ text: note }),
      });
      setNote("");
      await load();
      onUpdate();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={ref}
      className="session-dialog"
      aria-label={`${task.project} 작업 상세`}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="dialog-inner">
        <header>
          <span className="eyebrow">SESSION DETAIL</span>
          <button
            autoFocus
            className="icon-button"
            aria-label="상세 닫기"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </header>
        <div className="dialog-title">
          <Mark provider={task.provider} />
          <div>
            <h2>{task.project}</h2>
            <p>
              {names[task.provider]} · {task.model || "모델 미확인"}
            </p>
          </div>
        </div>
        <p className="muted">
          {date(task.started_at)} ~ {date(task.occurred_at)}
        </p>
        <div className="detail-stat">
          <span>이 조회 기간에 수집된 토큰</span>
          <strong>{integer(task.usage.total_tokens)}</strong>
        </div>
        <div className="token-breakdown">
          <div>
            <span>입력</span>
            <b>{integer(task.usage.input_tokens)}</b>
          </div>
          <div>
            <span>출력</span>
            <b>{integer(task.usage.output_tokens)}</b>
          </div>
          <div>
            <span>캐시 읽기</span>
            <b>{integer(task.usage.cache_read_tokens)}</b>
          </div>
        </div>
        <p className="note-text">
          캐시 포함 방식은 도구마다 다릅니다. 위 총합에 캐시를 다시 더하지
          않습니다. 아래 근거는 세션 전체에서 최근 40건입니다.
        </p>
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        {!detail ? (
          <div className="loading">
            <LoaderCircle className="spin" />
            근거 불러오는 중
          </div>
        ) : (
          <>
            <div className="section-title">
              <h3>수집 근거</h3>
              <span>{detail.evidence.length}건</span>
            </div>
            <p className="note-text">
              원문과 코드를 복제하지 않은 로컬 기록 참조입니다. 도구 호출은 실행
              성공이나 작업 완료를 의미하지 않습니다.
            </p>
            <div className="evidence-list">
              {detail.evidence.map((e, i) => (
                <details key={i}>
                  <summary>
                    <Link2 size={13} />
                    {e.type === "usage"
                      ? "사용량 기록"
                      : e.type === "session_started"
                        ? "세션 시작"
                        : "도구 활동"}
                    <span>{time(e.time)}</span>
                  </summary>
                  <code>
                    {e.ref}
                    {e.available === false && (
                      <p>원본 파일에 접근할 수 없습니다.</p>
                    )}
                  </code>
                </details>
              ))}
            </div>
            <div className="section-title">
              <h3>내일의 나에게</h3>
              <MessageSquare size={16} />
            </div>
            {detail.notes.map((n) => (
              <div className="saved-note" key={n.id}>
                <p>{n.text}</p>
                <small>{date(n.created_at)}</small>
              </div>
            ))}
            <label className="sr-only" htmlFor="session-note">
              작업 메모
            </label>
            <textarea
              id="session-note"
              value={note}
              maxLength={2000}
              disabled={demo}
              onChange={(e) => setNote(e.target.value)}
              placeholder={
                demo
                  ? "예시 모드에서는 메모를 저장하지 않습니다."
                  : "어디까지 했나요? 다음에 확인할 일을 남겨보세요."
              }
            />
            <div className="dialog-actions">
              <button
                className="button"
                disabled={demo || busy || !note.trim()}
                onClick={() => save()}
              >
                메모 저장
              </button>
              <button
                className="button primary"
                disabled={demo || busy || !!detail.confirmed_at}
                onClick={() => save(true)}
              >
                <CheckCheck size={15} />
                {detail.confirmed_at ? "사용자 확인 완료" : "검토 완료로 표시"}
              </button>
            </div>
            <p className="note-text">
              사용자 확인은 테스트 통과 기록과 별도로 저장됩니다.
            </p>
          </>
        )}
      </div>
    </dialog>
  );
}

export default function App() {
  const [path, setPath] = useState(window.location.pathname);
  const [period, setPeriod] = useState("today"),
    [project, setProject] = useState("all"),
    [provider, setProvider] = useState("all");
  const [hostedDemo, setHostedDemo] = useState(false);
  const [privateMode, setPrivateMode] = useState(false);
  const [demo, setDemo] = useState(false),
    [data, setData] = useState<Overview | null>(null),
    [projects, setProjects] = useState<{ id: string; name: string }[]>([]);
  const [sources, setSources] = useState<Source[]>([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [syncing, setSyncing] = useState(false);
  const [selected, setSelected] = useState<Task | null>(null),
    [search, setSearch] = useState(""),
    [showCount, setShowCount] = useState(30),
    [auto, setAuto] = useState(false),
    [loadedAt, setLoadedAt] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const requestSequence = useRef(0);
  const load = useCallback(async () => {
    const requestId = ++requestSequence.current;
    try {
      const health = await api<{deployment: string}>("/health");
      const remote = health.deployment === "demo";
      setHostedDemo(remote);
      setPrivateMode(health.deployment === "private");
      if (remote && !demo) setDemo(true);
      const query = new URLSearchParams({
        period,
        project,
        provider,
        demo: String(remote || demo),
      });
      const [next, ps, ss] = await Promise.all([
        api<Overview>("/overview?" + query),
        api<{ id: string; name: string }[]>("/projects?demo=" + demo),
        api<Source[]>("/sources"),
      ]);
      if (requestId !== requestSequence.current) return;
      setData(next);
      setProjects(ps);
      setSources(ss);
      setLoadedAt(new Date().toISOString());
      setError("");
    } catch (e) {
      if (requestId === requestSequence.current)
        setError((e as Error).message + " 서버 실행 상태를 확인해 주세요.");
    } finally {
      if (requestId === requestSequence.current) setLoading(false);
    }
  }, [period, project, provider, demo]);
  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);
  useEffect(() => {
    const pop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);
  const navigate = (next: string) => {
    window.history.pushState({}, "", next);
    setPath(next);
    setSearch("");
    window.scrollTo({ top: 0 });
  };
  const sync = useCallback(
    async (id?: Provider) => {
      if (privateMode) {
        await load();
        setNotice("서버 수신 기록을 새로고침했습니다. 새 기록 전송은 노트북에서 실행하세요.");
        return;
      }
      setSyncing(true);
      setError("");
      setNotice("");
      try {
        const ss = await api<Source[]>("/sources");
        const targets = ss.filter((s) => s.available && (!id || s.id === id));
        if (!targets.length) {
          setNotice("연결할 수 있는 로컬 기록 경로가 없습니다.");
          return;
        }
        for (const s of targets)
          await api(`/sources/${s.id}/sync`, { method: "POST" });
        await load();
        setNotice("로컬 기록을 동기화했습니다.");
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setSyncing(false);
      }
    },
    [load, privateMode],
  );
  useEffect(() => {
    if (!auto || demo || privateMode) return;
    const timer = window.setInterval(() => {
      if (!syncing) void sync();
    }, 60000);
    return () => clearInterval(timer);
  }, [auto, demo, privateMode, syncing, sync]);
  const switchDemo = () => {
    setDemo(!demo);
    setData(null);
    setLoading(true);
    setProject("all");
    setProvider("all");
    setSelected(null);
    setNotice("");
  };
  const active = navigation.find((n) => n.path === path) || navigation[0];
  const tasks = (data?.tasks || []).filter((t) =>
    `${t.project} ${t.summary} ${t.model}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  const today = new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date());
  const periodName = {
    today: "오늘",
    week: "이번 주",
    month: "이번 달",
    all: "전체 기록",
  }[period];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          aria-label="제라도 작업실 대시보드"
          href="/"
          onClick={(e) => {
            e.preventDefault();
            navigate("/");
          }}
        >
          <span className="brand-icon">
            <Activity size={24} />
          </span>
          <span>
            GERARDO<small>AI WORKSPACE</small>
          </span>
        </a>
        <div className="workspace">
          <span className="avatar">G</span>
          <div>
            <strong>제라도의 작업실</strong>
            <small>Personal workspace</small>
          </div>
          <MoreHorizontal size={16} />
        </div>
        <span className="nav-caption">WORKSPACE</span>
        <nav aria-label="주 메뉴">
          {navigation.map((n) => (
            <button
              key={n.path}
              aria-label={n.label}
              title={n.label}
              aria-current={active.path === n.path ? "page" : undefined}
              className={`nav-item ${active.path === n.path ? "active" : ""}`}
              onClick={() => navigate(n.path)}
            >
              <n.icon size={18} />
              <span className="nav-label">{n.label}</span>
              <span className="nav-short">{n.shortLabel}</span>
              {n.path === "/sources" && (
                <span className="nav-count">
                  {sources.filter((s) => s.available).length}/3
                </span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-box">
            <ShieldCheck size={18} />
            <strong>{hostedDemo ? "VPS 체험용 작업실" : privateMode ? "나의 비공개 VPS 작업실" : "내 노트북 안에서만"}</strong>
            <p>
              {hostedDemo ? "합성 예시 데이터만 표시합니다." : privateMode ? "노트북에서 전송한 메타데이터입니다." : "활동 기록은 로컬에 보관됩니다."}
              <br />
              원본 대화와 코드는 복제하지 않아요.
            </p>
            <span>
              <i /> {hostedDemo ? "DEMO WORKSPACE" : privateMode ? "PRIVATE WORKSPACE" : "LOCAL WORKSPACE"}
            </span>
          </div>
          <div className="profile">
            <span className="avatar">G</span>
            <div>
              <strong>Gerardo</strong>
              <small>함께 만드는 하루</small>
            </div>
            <span className="profile-dot" />
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            <span>나의 작업실</span>
            <ChevronRight size={13} />
            <strong>{active.label}</strong>
          </div>
          <div className="topbar-actions">
            {privateMode && <form method="post" action="/auth/logout"><button className="demo-button" type="submit">로그아웃</button></form>}
            <span className="local-chip">
              <ShieldCheck size={12} /> {hostedDemo ? "VPS 체험판" : privateMode ? "VPS 실제 기록" : "로컬 전용"}
            </span>
            <button
              className={`demo-button ${demo ? "selected" : ""}`}
              onClick={switchDemo}
              disabled={hostedDemo}
            >
              <FlaskConical size={14} />
              {hostedDemo ? "읽기 전용" : demo ? "실제 기록으로" : "예시 둘러보기"}
            </button>
            <span className="avatar small-avatar">G</span>
          </div>
        </header>
        <div className="page">
          <div className="page-heading">
            <div>
              <p className="eyebrow">YOUR AI, IN ONE PLACE</p>
              <h1>
                {path === "/" ? "제라도의 AI 활동 모니터링" : active.label}
              </h1>
              <p className="page-subtitle">
                {path === "/"
                  ? "세 AI와 함께 만든 오늘의 기록. 흐름을 보고, 다음 작업을 이어가세요."
                  : path === "/sources"
                    ? "연결 가능한 기록과 수집 범위를 확인하세요."
                    : path === "/usage"
                      ? "얼마나 사용했는지, 어떤 작업에 쓰였는지 함께 살펴보세요."
                      : path === "/projects"
                        ? "여러 도구에 흩어진 작업을 프로젝트별로 모았습니다."
                        : "기록을 따라가며 작업의 맥락을 되짚어보세요."}
              </p>
            </div>
            <div className="heading-actions">
              <span className="today">{today}</span>
              <button
                className="button"
                disabled={syncing || demo}
                onClick={() => sync()}
              >
                <RefreshCw size={14} className={syncing ? "spin" : ""} />
                {syncing ? "수집 중…" : privateMode ? "수신 기록 새로고침" : "지금 동기화"}
              </button>
            </div>
          </div>
          {demo && (
            <div className="demo-banner">
              <FlaskConical size={17} />
              <div>
                <strong>예시 모드입니다.</strong> 화면을 살펴보기 위한 합성
                데이터이며 실제 사용량과 분리되어 있습니다.
              </div>
              {!hostedDemo && <button onClick={switchDemo}>
                실제 기록 보기 <ArrowRight size={14} />
              </button>}
            </div>
          )}
          {error && (
            <div className="error" role="alert">
              <Unplug size={17} />
              <span>
                {error}
                {data ? " 마지막으로 불러온 화면을 표시합니다." : ""}
              </span>
              <button onClick={() => load()}>다시 시도</button>
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              <Check size={15} />
              {notice}
              <button aria-label="알림 닫기" onClick={() => setNotice("")}>
                <X size={14} />
              </button>
            </div>
          )}
          {path !== "/sources" && (
            <div className="filter-bar">
              <div className="period-tabs" aria-label="조회 기간">
                {[
                  ["today", "오늘"],
                  ["week", "이번 주"],
                  ["month", "이번 달"],
                  ["all", "전체"],
                ].map(([id, label]) => (
                  <button
                    key={id}
                    aria-pressed={period === id}
                    className={period === id ? "active" : ""}
                    onClick={() => setPeriod(id)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="filter-selects">
                <label>
                  <FolderOpen size={14} />
                  <span className="sr-only">프로젝트 필터</span>
                  <select
                    aria-label="프로젝트 필터"
                    value={project}
                    onChange={(e) => setProject(e.target.value)}
                  >
                    <option value="all">모든 프로젝트</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className="sr-only">AI 도구 필터</span>
                  <select
                    aria-label="AI 도구 필터"
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                  >
                    <option value="all">모든 AI</option>
                    {providers.map((p) => (
                      <option key={p} value={p}>
                        {names[p]}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <span className="refresh-status">
                {loading ? (
                  <>
                    <LoaderCircle size={12} className="spin" />
                    불러오는 중
                  </>
                ) : (
                  <>
                    <span className="live-dot" />
                    {loadedAt ? `${time(loadedAt)} 조회` : ""}
                  </>
                )}
              </span>
            </div>
          )}
          {loading && !data ? (
            <div className="loading large">
              <LoaderCircle className="spin" />
              작업실을 불러오고 있습니다.
            </div>
          ) : path === "/sources" ? (
            <>
              <div className="sources-intro">
                <Database size={24} />
                <div>
                  <h2>기록을 연결하면, 흐름이 보입니다.</h2>
                  <p>
                    {privateMode ? "노트북에서 보낸 실제 메타데이터를 표시합니다. 새 전송은 노트북의 전송 명령을 실행하세요." : "Claude와 Codex의 지정된 로컬 JSONL 기록을 읽습니다. 원본은 변경하지 않습니다."}
                  </p>
                </div>
                <label className="auto-switch">
                  <input
                    type="checkbox"
                    checked={auto}
                    disabled={demo || privateMode}
                    onChange={(e) => setAuto(e.target.checked)}
                  />{" "}
                  1분마다 동기화
                </label>
              </div>
              <div className="source-list">
                {sources.map((s) => (
                  <article className="source-panel" key={s.id}>
                    <div className="source-heading">
                      <Mark provider={s.id} />
                      <div>
                        <h2>{s.name}</h2>
                        <code>{s.location}</code>
                      </div>
                      <span className={`status ${s.status}`}>
                        <i />
                        {stateName(s.status)}
                      </span>
                    </div>
                    <div className="source-facts">
                      <div>
                        <span>수집 범위</span>
                        <strong>
                          {s.available
                            ? `최근 수정 파일 최대 ${s.scan_limit}개`
                            : "지원 경로 미확인"}
                        </strong>
                      </div>
                      <div>
                        <span>마지막 성공</span>
                        <strong>{date(s.last_success_at)}</strong>
                      </div>
                      <div>
                        <span>{privateMode ? "서버 최종 수신" : "최근 스캔 파일"}</span>
                        <strong>
                          {privateMode ? date(s.last_received_at ?? null) : `${s.files} / ${s.total_files ?? "미확인"}`}
                        </strong>
                      </div>
                      <div>
                        <span>검토할 수집 경고</span>
                        <strong>{s.warnings}건</strong>
                      </div>
                    </div>
                    <div className="source-bottom">
                      <p>
                        {s.error ||
                          "세션 · 모델 · 토큰 · 도구 호출 정보를 수집합니다. 요금과 잔여 한도는 수집하지 않습니다."}
                      </p>
                      <button
                        className="button"
                        disabled={!s.available || syncing || demo || privateMode}
                        onClick={() => sync(s.id)}
                      >
                        <RefreshCw size={14} />
                        {privateMode ? "노트북에서 전송" : s.available ? "동기화" : "연결 미확인"}
                      </button>
                    </div>
                  </article>
                ))}
              </div>
              <div className="info-panel">
                <CircleHelp size={19} />
                <div>
                  <strong>수집 범위에 대해</strong>
                  <p>
                    최초 연결은 최근 수정 파일 100개씩 시작합니다. 이전에 수집한
                    기록은 보존됩니다. Antigravity는 현재 확인한 설치·로그
                    경로에서 지원 가능한 기록을 찾지 못했습니다. 다른 설치
                    위치나 내보내기 형식이 확인되면 어댑터를 추가할 수 있습니다.
                  </p>
                </div>
              </div>
            </>
          ) : (
            data && (
              <>
                {path === "/" && (
                  <>
                    <section className="briefing">
                      <div className="briefing-icon">
                        <Sparkles size={24} />
                      </div>
                      <div className="briefing-copy">
                        <div className="briefing-title">
                          <h2>{periodName}의 작업 브리핑</h2>
                          <span>기록 기반 요약</span>
                        </div>
                        <p>{data.briefing}</p>
                        <div className="briefing-meta">
                          <span>
                            <FolderOpen size={12} />
                            {data.projects.length}개 프로젝트
                          </span>
                          <span>
                            <Link2 size={12} />
                            사용량 확인 {data.coverage.providers_with_usage}/3개
                            도구
                          </span>
                        </div>
                      </div>
                      <div className="orbital" aria-hidden="true">
                        <div className="orbit-ring" />
                        <span className="orbit-center">G</span>
                        <span className="orbit-node one">
                          <Sparkles size={16} />
                        </span>
                        <span className="orbit-node two">
                          <Code2 size={16} />
                        </span>
                        <span className="orbit-node three">
                          <Box size={16} />
                        </span>
                      </div>
                    </section>
                    <div className="stats-grid">
                      <div className="stat">
                        <div>
                          <span>수집된 토큰</span>
                          <Zap size={16} />
                        </div>
                        <strong>
                          {compact(data.usage.total_tokens)}
                          <small>tokens</small>
                        </strong>
                        <p>
                          {data.coverage.providers_with_usage}/3개 도구 ·{" "}
                          {data.usage.included_count}개 사용량 기록
                        </p>
                      </div>
                      <div className="stat">
                        <div>
                          <span>활동 세션</span>
                          <Terminal size={16} />
                        </div>
                        <strong>
                          {data.sessions}
                          <small>sessions</small>
                        </strong>
                        <p>기록이 있는 작업 세션</p>
                      </div>
                      <div className="stat">
                        <div>
                          <span>확인 완료</span>
                          <CheckCheck size={16} />
                        </div>
                        <strong>
                          {data.confirmed}
                          <small>sessions</small>
                        </strong>
                        <p>직접 검토한 작업 기록</p>
                      </div>
                      <div className="stat">
                        <div>
                          <span>검토 대기</span>
                          <Clock3 size={16} />
                        </div>
                        <strong>
                          {data.pending}
                          <small>sessions</small>
                        </strong>
                        <p>다음 작업 전 확인해 보세요</p>
                      </div>
                    </div>
                    <div className="section-title">
                      <h2>
                        함께 일하는 AI <span>3</span>
                      </h2>
                      <button
                        className="text-button"
                        onClick={() => navigate("/sources")}
                      >
                        연결 관리 <ArrowRight size={14} />
                      </button>
                    </div>
                    <div className="tools-grid">
                      {data.providers.map((tool) => (
                        <ToolCard
                          key={tool.id}
                          tool={tool}
                          onClick={() => {
                            setProvider(tool.id);
                            navigate("/activity");
                          }}
                        />
                      ))}
                    </div>
                    <div className="content-grid">
                      <section className="panel">
                        <div className="panel-heading">
                          <div>
                            <h2>토큰 사용 흐름</h2>
                            <p>수집된 사용량을 도구별로 살펴보세요.</p>
                          </div>
                          <button
                            className="icon-button"
                            aria-label="토큰 분석 열기"
                            onClick={() => navigate("/usage")}
                          >
                            <ArrowUpRight size={18} />
                          </button>
                        </div>
                        <Chart points={data.series} />
                      </section>
                      <section className="panel project-panel">
                        <div className="panel-heading">
                          <div>
                            <h2>진행 중인 프로젝트</h2>
                            <p>선택한 기간의 작업 기록</p>
                          </div>
                          <FolderOpen size={17} />
                        </div>
                        {data.projects.length ? (
                          data.projects.slice(0, 4).map((p) => (
                            <button
                              className="project-mini"
                              key={p.id}
                              onClick={() => {
                                setProject(p.id);
                                navigate("/projects");
                              }}
                            >
                              <span className="folder-icon">
                                <FolderOpen size={18} />
                              </span>
                              <div>
                                <strong>{p.name}</strong>
                                <span>
                                  {p.sessions}개 세션 ·{" "}
                                  {compact(p.usage.total_tokens)} tokens
                                </span>
                              </div>
                              <ChevronRight size={14} />
                            </button>
                          ))
                        ) : (
                          <Empty
                            title="연결된 프로젝트가 없습니다."
                            body="기록에서 작업 폴더를 확인하면 표시됩니다."
                          />
                        )}
                        <button
                          className="panel-link"
                          onClick={() => navigate("/projects")}
                        >
                          프로젝트 모두 보기 <ArrowRight size={14} />
                        </button>
                      </section>
                    </div>
                    <section className="panel timeline-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>최근 작업 타임라인</h2>
                          <p>한 세션씩 열어 근거를 확인하고 메모를 남기세요.</p>
                        </div>
                        <button
                          className="text-button"
                          onClick={() => navigate("/activity")}
                        >
                          모든 활동 <ArrowRight size={14} />
                        </button>
                      </div>
                      {tasks.length ? (
                        <TaskRows tasks={tasks} onSelect={setSelected} />
                      ) : (
                        <Empty action={() => navigate("/sources")} />
                      )}
                    </section>
                  </>
                )}
                {path === "/activity" && (
                  <section className="panel">
                    <div className="panel-heading">
                      <div>
                        <h2>
                          작업의 흐름{" "}
                          <span className="count">{tasks.length}</span>
                        </h2>
                        <p>
                          확인 완료는 사용자 검토 상태이며 테스트 통과 여부와
                          다릅니다.
                        </p>
                      </div>
                      <label className="search-field">
                        <Search size={15} />
                        <input
                          value={search}
                          onChange={(e) => {
                            setSearch(e.target.value);
                            setShowCount(30);
                          }}
                          aria-label="활동 검색"
                          placeholder="프로젝트, 도구 호출 검색"
                        />
                      </label>
                    </div>
                    {tasks.length ? (
                      <>
                        <TaskRows
                          tasks={tasks}
                          limit={showCount}
                          onSelect={setSelected}
                        />
                        {tasks.length > showCount && (
                          <button
                            className="panel-link"
                            onClick={() => setShowCount(showCount + 30)}
                          >
                            30개 더 보기
                          </button>
                        )}
                      </>
                    ) : (
                      <Empty />
                    )}
                  </section>
                )}
                {path === "/projects" && (
                  <div className="projects-grid">
                    {data.projects.length ? (
                      data.projects.map((p) => (
                        <section className="panel project-card" key={p.id}>
                          <div className="project-card-top">
                            <span className="folder-icon">
                              <FolderOpen size={23} />
                            </span>
                            <div className="project-tools">
                              {p.providers.map((k) => (
                                <Mark key={k} provider={k} size="small" />
                              ))}
                            </div>
                          </div>
                          <h2>{p.name}</h2>
                          <p>{p.sessions}개의 작업 세션이 연결되어 있습니다.</p>
                          <div className="project-total">
                            <span>수집된 토큰</span>
                            <strong>{compact(p.usage.total_tokens)}</strong>
                          </div>
                          <button
                            className="panel-link"
                            onClick={() => {
                              setProject(p.id);
                              navigate("/activity");
                            }}
                          >
                            작업 기록 열기 <ArrowRight size={14} />
                          </button>
                        </section>
                      ))
                    ) : (
                      <Empty />
                    )}
                  </div>
                )}
                {path === "/usage" && (
                  <>
                    <div className="usage-summary">
                      <div>
                        <span className="eyebrow">COLLECTED USAGE</span>
                        <strong>
                          {integer(data.usage.total_tokens)}
                          <small>tokens</small>
                        </strong>
                        <p>
                          {data.coverage.missing_providers.length
                            ? `${data.coverage.missing_providers.join(", ")} 사용량은 이 기간에 미수집입니다.`
                            : "선택한 기간에 세 도구의 사용량이 확인되었습니다."}
                        </p>
                      </div>
                      <div className="usage-split">
                        <div>
                          <ArrowDownLeft size={18} />
                          <span>입력 토큰</span>
                          <strong>{compact(data.usage.input_tokens)}</strong>
                        </div>
                        <div>
                          <ArrowUpRight size={18} />
                          <span>출력 토큰</span>
                          <strong>{compact(data.usage.output_tokens)}</strong>
                        </div>
                      </div>
                    </div>
                    <section className="panel">
                      <div className="panel-heading">
                        <div>
                          <h2>일별 토큰 사용량</h2>
                          <p>
                            단위: tokens · 그래프는 최근 최대 62일을 표시합니다.
                          </p>
                        </div>
                      </div>
                      <Chart points={data.series} extended />
                    </section>
                    <div className="tools-grid usage-tools">
                      {data.providers.map((tool) => (
                        <ToolCard
                          key={tool.id}
                          tool={tool}
                          onClick={() => {
                            setProvider(tool.id);
                            navigate("/activity");
                          }}
                        />
                      ))}
                    </div>
                    <div className="info-panel">
                      <CircleHelp size={18} />
                      <div>
                        <strong>사용량과 요금은 다릅니다.</strong>
                        <p>
                          캐시 포함 방식은 도구별로 다릅니다. 원본 사용량 의미를
                          확인해 정규화하며, 월 구독료나 잔여 한도를 토큰으로
                          추정하지 않습니다. 기록의 관측 시각을 기준으로 날짜에
                          배분합니다.
                        </p>
                      </div>
                    </div>
                  </>
                )}
              </>
            )
          )}
          <footer className="footer">
            <span>
              <ShieldCheck size={12} /> {hostedDemo ? "제라도의 AI 작업실 · VPS 체험판" : privateMode ? "제라도의 비공개 VPS 작업실" : "나만의 로컬 AI 작업실"}
            </span>
            <span>
              Asia/Seoul · {demo ? "합성 예시 데이터" : privateMode ? "노트북에서 전송한 실제 기록" : "읽기 전용 소스 수집"}
            </span>
          </footer>
        </div>
      </main>
      {selected && (
        <SessionDialog
          task={selected}
          demo={demo}
          onClose={() => setSelected(null)}
          onUpdate={load}
        />
      )}
    </div>
  );
}
