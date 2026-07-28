use rayon::prelude::*;
use regex::Regex;
use std::fs::File;
use std::sync::Arc;
use serde::{Serialize, Deserialize};

#[derive(Clone)]
pub struct LogEngine {
    lines: Arc<Vec<String>>,
}

// Struct to represent a filter configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FilterItem {
    pub text: String,
    pub is_regex: bool,
    pub is_exclude: bool,
    pub is_event: bool,
    pub idx: usize,
}

impl LogEngine {
    pub fn new(path: &str) -> Result<Self, String> {
        let file = File::open(path).map_err(|e| e.to_string())?;
        let mmap = unsafe { memmap2::Mmap::map(&file).map_err(|e| e.to_string())? };

        // Handle Encoding with BOM removal
        let (decoded, _encoding_used, _had_errors) = encoding_rs::UTF_8.decode(&mmap);
        let content = decoded.into_owned();

        // Split lines handling \r\n, \n, and \r
        let mut lines = Vec::new();
        for line in content.lines() {
            let mut s = line.to_string();
            s.push('\n');
            lines.push(s);
        }

        Ok(LogEngine {
            lines: Arc::new(lines),
        })
    }

    pub fn get_line(&self, index: usize) -> String {
        self.lines.get(index).cloned().unwrap_or_default()
    }

    pub fn line_count(&self) -> usize {
        self.lines.len()
    }

    pub fn search(&self, query: &str, is_regex: bool, case_sensitive: bool) -> Result<Vec<usize>, String> {
        let lines = &self.lines;

        let results: Vec<usize> = if is_regex {
            let re = regex::RegexBuilder::new(query)
                .case_insensitive(!case_sensitive)
                .build()
                .map_err(|e| e.to_string())?;

            lines.par_iter()
                .enumerate()
                .filter_map(|(i, line)| {
                    if re.is_match(line) { Some(i) } else { None }
                })
                .collect()
        } else {
            if case_sensitive {
                lines.par_iter()
                    .enumerate()
                    .filter_map(|(i, line)| {
                        if line.contains(query) { Some(i) } else { None }
                    })
                    .collect()
            } else {
                let re = regex::RegexBuilder::new(&regex::escape(query))
                    .case_insensitive(true)
                    .build()
                    .map_err(|e| e.to_string())?;

                lines.par_iter()
                    .enumerate()
                    .filter_map(|(i, line)| {
                        if re.is_match(line) { Some(i) } else { None }
                    })
                    .collect()
            }
        };

        Ok(results)
    }

    pub fn filter(
        &self,
        filters: &[FilterItem], 
    ) -> Result<(Vec<u8>, Vec<usize>, Vec<usize>, Vec<(String, String, usize)>), String> {

        let lines = &self.lines;

        let compiled_filters: Vec<_> = filters.iter().map(|f| {
            let re = if f.is_regex {
                Regex::new(&f.text).ok()
            } else {
                None
            };
            (f.text.clone(), re, f.is_regex, f.is_exclude, f.is_event, f.idx)
        }).collect();

        let ts_regex = Regex::new(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\b\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b)").unwrap();

        let results: Vec<(u8, Option<usize>, Option<(String, String, usize)>)> = lines.par_iter().enumerate().map(|(raw_idx, line)| {
            let mut tag_code: u8 = 0; 
            let mut event_data = None;
            let mut matched_filter_idx = None;

            for (i, (text, re, is_regex, is_exclude, _, _)) in compiled_filters.iter().enumerate() {
                if !*is_exclude { continue; }
                let matched = if *is_regex {
                    re.as_ref().map_or(false, |r| r.is_match(line))
                } else {
                    line.contains(text)
                };

                if matched {
                    tag_code = 1; 
                    matched_filter_idx = Some(i);
                    break;
                }
            }

            if tag_code == 0 {
                for (i, (text, re, is_regex, is_exclude, is_event, _)) in compiled_filters.iter().enumerate() {
                    if *is_exclude { continue; }

                    let matched = if *is_regex {
                        re.as_ref().map_or(false, |r| r.is_match(line))
                    } else {
                        line.contains(text)
                    };

                    if matched {
                        tag_code = (2 + i) as u8;
                        matched_filter_idx = Some(i);

                        if *is_event {
                            if let Some(caps) = ts_regex.captures(line) {
                                if let Some(m) = caps.get(1) {
                                    event_data = Some((m.as_str().to_string(), text.clone(), raw_idx));
                                }
                            }
                        }
                        break; 
                    }
                }
            }

            (tag_code, matched_filter_idx, event_data)
        }).collect();

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
