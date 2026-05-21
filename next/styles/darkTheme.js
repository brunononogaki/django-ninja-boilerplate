export const darkStyles = `
  @keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-16px); }
  }
  .orb { animation: float 8s ease-in-out infinite; }
  .orb-2 { animation: float 10s ease-in-out 2s infinite; }
  .dark-input {
    width: 100%;
    padding: 10px 16px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    color: #fff;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  .dark-input::placeholder { color: rgba(255,255,255,0.25); }
  .dark-input:focus { border-color: rgba(99,102,241,0.6); }
  .dark-input:disabled { opacity: 0.4; cursor: not-allowed; }
  .dark-label {
    display: block;
    font-size: 13px;
    color: rgba(255,255,255,0.5);
    margin-bottom: 6px;
    font-weight: 500;
  }
`;
