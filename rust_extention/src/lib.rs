use pyo3::prelude::*;
use rayon::prelude::*;
use regex::Regex;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::sync::Arc;

#[pyclass]
struct LogEngine {
    lines: Arc<Vec<String>>,
}

#[pymethods]
impl LogEngine {
    #[new]
    fn new(path: &str) -> PyResult<Self> {
        let file = File::open(path)?;
        let mut reader = BufReader::new(file);
        
        let mut lines = Vec::new();
        let mut buf = Vec::new();
        
        loop {
            buf.clear();
            match reader.read_until(b'\n', &mut buf) {
                Ok(0) => break, // EOF
                Ok(_) => {
                    let mut s = String::from_utf8_lossy(&buf).into_owned();
                    // Handle Universal Newlines: trim trailing \n and \r
                    if s.ends_with('\n') { s.pop(); }
                    if s.ends_with('\r') { s.pop(); }

                    // If there are remaining \r inside, split them (Mixed line endings)
                    if s.contains('\r') {
                        for part in s.split('\r') {
                            let mut line = part.to_string();
                            line.push('\n');
                            lines.push(line);
                        }
                    } else {
                        s.push('\n');
                        lines.push(s);
                    }
                },
                Err(e) => return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string())),
            }
        }

        Ok(LogEngine {
            lines: Arc::new(lines),
        })
    }

    fn get_line(&self, index: usize) -> String {
        self.lines.get(index).cloned().unwrap_or_default()
    }

    fn line_count(&self) -> usize {
        self.lines.len()
    }

    // 回傳: (line_tags_indices, filtered_indices, hit_counts, timeline_events)
    // line_tags_indices: 0=None, 1=EXCLUDED, 2=filter_0, 3=filter_1...
    fn filter(
        &self, 
        filters: Vec<(String, bool, bool, bool, usize)>, // (text, is_regex, is_exclude, is_event, original_index)
    ) -> PyResult<(Vec<u8>, Vec<usize>, Vec<usize>, Vec<(String, String, usize)>)> {
        
        let lines = &self.lines;
        
        // 預先編譯 Regex 以提升效能
        let compiled_filters: Vec<_> = filters.iter().map(|(text, is_regex, is_exclude, is_event, idx)| {
            let re = if *is_regex {
                Regex::new(text).ok()
            } else {
                None
            };
            (text.clone(), re, *is_regex, *is_exclude, *is_event, *idx)
        }).collect();

        // Timestamp Regex (與 Python 端一致)
        let ts_regex = Regex::new(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\b\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b)").unwrap();

        // 使用 Rayon 進行平行處理
        // 我們將計算結果分為幾個部分，最後再合併
        let results: Vec<(u8, Option<usize>, Option<(String, String, usize)>)> = lines.par_iter().enumerate().map(|(raw_idx, line)| {
            let mut tag_code: u8 = 0; // 0 = None
            let mut event_data = None;
            let mut matched_filter_idx = None;

            // 1. Check Excludes
            for (i, (text, re, is_regex, is_exclude, _, _)) in compiled_filters.iter().enumerate() {
                if !*is_exclude { continue; }
                let matched = if *is_regex {
                    re.as_ref().map_or(false, |r| r.is_match(line))
                } else {
                    line.contains(text)
                };

                if matched {
                    tag_code = 1; // 1 = EXCLUDED
                    matched_filter_idx = Some(i);
                    break; 
                }
            }

            // 2. Check Includes (if not excluded)
            if tag_code == 0 {
                for (i, (text, re, is_regex, is_exclude, is_event, _)) in compiled_filters.iter().enumerate() {
                    if *is_exclude { continue; }
                    
                    let matched = if *is_regex {
                        re.as_ref().map_or(false, |r| r.is_match(line))
                    } else {
                        line.contains(text)
                    };

                    if matched {
                        // Tag mapping: 2 + filter_index
                        // 注意：這裡的 i 是 compiled_filters 的索引，對應 Python 傳入的順序
                        tag_code = (2 + i) as u8;
                        matched_filter_idx = Some(i);
                        
                        if *is_event {
                            if let Some(caps) = ts_regex.captures(line) {
                                if let Some(m) = caps.get(1) {
                                    event_data = Some((m.as_str().to_string(), text.clone(), raw_idx));
                                }
                            }
                        }
                        break; // First match wins
                    }
                }
            }

            (tag_code, matched_filter_idx, event_data)
        }).collect();

        // Post-processing (Single thread is fast enough for aggregation)
        let mut line_tags_codes = Vec::with_capacity(lines.len());
        let mut filtered_indices = Vec::new();
        let mut hit_counts = vec![0; filters.len()];
        let mut timeline_events = Vec::new();

        for (raw_idx, (code, matched_idx, event)) in results.into_iter().enumerate() {
            line_tags_codes.push(code);
            
            if let Some(idx) = matched_idx {
                hit_counts[idx] += 1;
            }

            if code >= 2 {
                filtered_indices.push(raw_idx);
                
                if let Some(evt) = event {
                    timeline_events.push(evt);
                }
            }
        }

        Ok((line_tags_codes, filtered_indices, hit_counts, timeline_events))
    }
}

#[pymodule]
fn log_engine_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<LogEngine>()?;
    Ok(())
}
