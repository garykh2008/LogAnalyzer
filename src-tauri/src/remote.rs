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
    sess.handshake().map_err(|e| {
        let mut msg = format!("SSH handshake failed: {}", e);
        // A KEX_FAILURE (-5) is almost always an algorithm mismatch rather than
        // a network problem: the target offers only kex/host-key methods this
        // libssh2 build can't do. Say which ones it *can* do, otherwise the user
        // is stuck comparing against working `ssh.exe` with no way to tell why.
        // libssh2's own LIBSSH2_ERROR_KEX_FAILURE; ssh2 does not re-export the
        // constant, so match the value it documents.
        const KEX_FAILURE: i32 = -5;
        if let ssh2::ErrorCode::Session(code) = e.code() {
            if code == KEX_FAILURE {
                msg.push_str(&format!(
                    "\nClient supports kex [{}] and hostkey [{}]; \
                     the target must offer at least one of each.",
                    supported(&sess, ssh2::MethodType::Kex),
                    supported(&sess, ssh2::MethodType::HostKey),
                ));
            }
        }
        msg
    })?;
    sess.userauth_password(&cfg.user, &cfg.password)
        .map_err(|e| format!("SSH authentication failed: {}", e))?;
    if !sess.authenticated() {
        return Err("SSH authentication failed".to_string());
    }
    Ok(sess)
}

/// Comma-joined list of the algorithms this build supports, for error messages.
fn supported(sess: &Session, kind: ssh2::MethodType) -> String {
    match sess.supported_algs(kind) {
        Ok(algs) => algs.join(", "),
        Err(_) => "?".to_string(),
    }
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
