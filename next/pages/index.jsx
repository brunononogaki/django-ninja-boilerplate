import Head from "next/head";
import Link from "next/link";

export default function Landing() {
  return (
    <>
      <Head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap"
          rel="stylesheet"
        />
        <style>{`
          @keyframes float {
            0%, 100% { transform: translateY(0px) scale(1); }
            50% { transform: translateY(-20px) scale(1.02); }
          }
          @keyframes fadeUp {
            from { opacity: 0; transform: translateY(24px); }
            to { opacity: 1; transform: translateY(0); }
          }
          .anim-1 { animation: fadeUp 0.7s ease both; }
          .anim-2 { animation: fadeUp 0.7s ease 0.1s both; }
          .anim-3 { animation: fadeUp 0.7s ease 0.2s both; }
          .anim-4 { animation: fadeUp 0.7s ease 0.35s both; }
          .orb { animation: float 8s ease-in-out infinite; }
          .orb-2 { animation: float 10s ease-in-out 2s infinite; }
          .btn-primary:hover { box-shadow: 0 0 48px rgba(99, 102, 241, 0.7); transform: translateY(-1px); }
          .btn-primary { transition: all 0.2s ease; }
          .btn-secondary:hover { background: rgba(255,255,255,0.07); border-color: rgba(255,255,255,0.4); transform: translateY(-1px); }
          .btn-secondary { transition: all 0.2s ease; }
        `}</style>
      </Head>

      <div
        className="min-h-screen flex items-center justify-center relative overflow-hidden"
        style={{ background: "#07070f", fontFamily: "'DM Sans', sans-serif" }}
      >
        {/* Dot grid background */}
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: "radial-gradient(circle, rgba(99,102,241,0.18) 1px, transparent 1px)",
            backgroundSize: "44px 44px",
            maskImage: "radial-gradient(ellipse 80% 80% at 50% 50%, black 40%, transparent 100%)",
          }}
        />

        {/* Gradient orbs */}
        <div
          className="orb absolute rounded-full"
          style={{
            width: 500,
            height: 500,
            top: "-120px",
            left: "-100px",
            background: "radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 70%)",
            filter: "blur(40px)",
          }}
        />
        <div
          className="orb-2 absolute rounded-full"
          style={{
            width: 400,
            height: 400,
            bottom: "-80px",
            right: "-80px",
            background: "radial-gradient(circle, rgba(139,92,246,0.18) 0%, transparent 70%)",
            filter: "blur(40px)",
          }}
        />

        {/* Content */}
        <div className="relative z-10 text-center px-6 max-w-2xl mx-auto">
          {/* Badge */}
          <div className="anim-1 inline-flex items-center gap-2 rounded-full px-4 py-1.5 mb-10" style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.1)",
          }}>
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" style={{ boxShadow: "0 0 6px #818cf8" }} />
            <span className="text-xs tracking-widest uppercase" style={{ color: "rgba(255,255,255,0.45)", letterSpacing: "0.12em" }}>
              Open Source Boilerplate
            </span>
          </div>

          {/* Headline */}
          <h1
            className="anim-2 mb-6 leading-none tracking-tight"
            style={{
              fontFamily: "'Syne', sans-serif",
              fontWeight: 800,
              fontSize: "clamp(3rem, 8vw, 5.5rem)",
              color: "#fff",
            }}
          >
            Your next SaaS,{" "}
            <span style={{
              background: "linear-gradient(120deg, #818cf8 0%, #a78bfa 45%, #e879f9 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}>
              built faster.
            </span>
          </h1>

          {/* Subtitle */}
          <p
            className="anim-3 mb-12 leading-relaxed"
            style={{
              color: "rgba(255,255,255,0.42)",
              fontSize: "1.15rem",
              fontWeight: 300,
              maxWidth: "440px",
              margin: "0 auto 3rem",
            }}
          >
            Django Ninja + Next.js. Auth, CRUD, email, and deploy&nbsp;— all wired up and ready to ship.
          </p>

          {/* CTA Buttons */}
          <div className="anim-4 flex items-center justify-center gap-4 flex-wrap">
            <Link
              href="/login"
              className="btn-primary px-9 py-3.5 rounded-xl font-medium text-white text-base"
              style={{
                background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                boxShadow: "0 0 32px rgba(99,102,241,0.45)",
              }}
            >
              Login
            </Link>
            <Link
              href="/registration"
              className="btn-secondary px-9 py-3.5 rounded-xl font-medium text-base"
              style={{
                color: "rgba(255,255,255,0.75)",
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.18)",
                backdropFilter: "blur(8px)",
              }}
            >
              Sign Up
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
