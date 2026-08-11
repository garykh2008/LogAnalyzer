// Minimal SSH helpers for remote capture (M4).
//
// Uses ssh2 (libssh2) in blocking mode. Commands are wrapped as PowerShell
// `-EncodedCommand` payloads so we never fight remote quoting rules.

use std::io::Read;
use std::net::TcpStream;
use std::time::Duration;

use base64::Engine;
use ssh2::Session;

pub struct SshConfig {
    pub host: String,
    pub port: u16,
    pub user: String,
    pub password: String,
}

/// Connect + authenticate with a password. Returns an authenticated session.
pub fn connect(cfg: &SshConfig) -> Result<Session, String> {
    let addr = format!("{}:{}", cfg.host, cfg.port);
    let tcp = TcpStream::connect(&addr).map_err(|e| format!("TCP connect to {} failed: {}", addr, e))?;
    tcp.set_read_timeout(Some(Duration::from_secs(30))).ok();

    let mut sess = Session::new().map_err(|e| e.to_string())?;
    sess.set_tcp_stream(tcp);
    sess.handshake().map_err(|e| format!("SSH handshake failed: {}", e))?;
    sess.userauth_password(&cfg.user, &cfg.password)
        .map_err(|e| format!("SSH authentication failed: {}", e))?;
    if !sess.authenticated() {
        return Err("SSH authentication failed".to_string());
    }
    Ok(sess)
}

/// Wrap a PowerShell script as a full `powershell -EncodedCommand <b64>` command
/// line (UTF-16LE + base64), sidestepping all shell quoting.
pub fn ps_command(script: &str) -> String {
    let mut utf16: Vec<u8> = Vec::with_capacity(script.len() * 2);
    for u in script.encode_utf16() {
        utf16.extend_from_slice(&u.to_le_bytes());
    }
    let b64 = base64::engine::general_purpose::STANDARD.encode(utf16);
    format!("powershell -NoProfile -EncodedCommand {}", b64)
}

/// Run a PowerShell script to completion (blocking). Returns (exit code, stdout).
pub fn run_ps(sess: &Session, script: &str) -> Result<(i32, String), String> {
    let mut ch = sess.channel_session().map_err(|e| e.to_string())?;
    ch.exec(&ps_command(script)).map_err(|e| e.to_string())?;
    let mut out = String::new();
    ch.read_to_string(&mut out).map_err(|e| e.to_string())?;
    ch.send_eof().ok();
    ch.wait_close().ok();
    let code = ch.exit_status().unwrap_or(-1);
    Ok((code, out))
}
