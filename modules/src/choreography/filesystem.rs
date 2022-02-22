use crate::choreography::{NetworkingStrategy, StorageStrategy};
use crate::execution::ExecutionContext;
use moose::prelude::*;
use notify::{DebouncedEvent, Watcher};
use serde::Deserialize;
use std::collections::HashMap;
use std::convert::TryFrom;
use std::path::Path;

pub struct FilesystemChoreography {
    own_identity: Identity,
    sessions_dir: String,
    networking_strategy: NetworkingStrategy,
    storage_strategy: StorageStrategy,
}

impl FilesystemChoreography {
    pub fn new(
        own_identity: Identity,
        sessions_dir: String,
        networking_strategy: NetworkingStrategy,
        storage_strategy: StorageStrategy,
    ) -> FilesystemChoreography {
        FilesystemChoreography {
            own_identity,
            sessions_dir,
            networking_strategy,
            storage_strategy,
        }
    }

    pub async fn listen(&self, ignore_existing: bool) -> Result<(), Box<dyn std::error::Error>> {
        if !ignore_existing {
            for entry in std::fs::read_dir(&self.sessions_dir)? {
                let entry = entry?;
                let path = entry.path();
                self.launch_session_from_path(&path).await?;
            }
        }

        let (tx, rx) = std::sync::mpsc::channel();
        let mut watcher = notify::watcher(tx.clone(), std::time::Duration::from_secs(2))?;
        watcher.watch(&self.sessions_dir, notify::RecursiveMode::Recursive)?;

        for event in rx {
            match event {
                DebouncedEvent::Create(path) => {
                    self.abort_session_from_path(&path).await?;
                    self.launch_session_from_path(&path).await?;
                }
                DebouncedEvent::Remove(path) => {
                    self.abort_session_from_path(&path).await?;
                }
                DebouncedEvent::Write(path) => {
                    self.abort_session_from_path(&path).await?;
                    self.launch_session_from_path(&path).await?;
                }
                DebouncedEvent::Rename(src_path, dst_path) => {
                    self.abort_session_from_path(&src_path).await?;
                    self.launch_session_from_path(&dst_path).await?;
                }
                _ => {
                    // ignore
                }
            }
        }

        Ok(())
    }

    async fn launch_session_from_path(
        &self,
        path: &Path,
    ) -> Result<(), Box<dyn std::error::Error>> {
        if path.is_file() {
            match path.extension() {
                Some(ext) if ext == "session" => {
                    let filename = path.file_stem().unwrap().to_string_lossy().to_string();
                    let session_id = SessionId::try_from(filename.as_str()).unwrap();

                    tracing::info!("Launching session from {:?}", filename);

                    let config = std::fs::read_to_string(path)?;
                    let session_config: SessionConfig = toml::from_str(&config)?;

                    let computation = {
                        let comp_path = &session_config.computation.path;
                        match session_config.computation.format {
                            Format::Binary => {
                                let comp_raw = std::fs::read(comp_path)?;
                                moose::computation::Computation::from_msgpack(comp_raw)?
                            }
                            Format::Textual => {
                                let comp_raw = std::fs::read_to_string(comp_path)?;
                                moose::computation::Computation::from_textual(&comp_raw)?
                            }
                        }
                    };

                    let role_assignments: HashMap<Role, Identity> = session_config
                        .roles
                        .into_iter()
                        .map(|role_config| {
                            let role = Role::from(&role_config.name);
                            let identity = Identity::from(&role_config.endpoint);
                            (role, identity)
                        })
                        .collect();

                    let networking = (self.networking_strategy)(session_id.clone());
                    let storage = (self.storage_strategy)();

                    let session =
                        ExecutionContext::new(self.own_identity.clone(), networking, storage);

                    let outputs = session
                        .execute_computation(session_id, &computation, role_assignments)
                        .await?;

                    for (output_name, output_value) in outputs {
                        let filename = filename.clone();
                        tokio::spawn(async move {
                            let value = output_value.await.unwrap();
                            tracing::info!(
                                "Output '{}' from '{:?}' ready: {:?}",
                                output_name,
                                filename,
                                value
                            );
                        });
                    }
                }
                Some(ext) if ext == "moose" => {
                    // ok to skip
                }
                _ => {
                    tracing::warn!("Skipping {:?}", path);
                }
            }
        }
        Ok(())
    }

    async fn abort_session_from_path(
        &self,
        _path: &Path,
    ) -> Result<(), Box<dyn std::error::Error>> {
        // TODO
        Ok(())
    }
}

#[derive(Debug, Deserialize)]
struct SessionConfig {
    computation: ComputationConfig,
    roles: Vec<RoleConfig>,
}

#[derive(Debug, Deserialize)]
struct ComputationConfig {
    path: String,
    format: Format,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "lowercase")]
enum Format {
    Binary,
    Textual,
}

#[derive(Debug, Deserialize)]
struct RoleConfig {
    name: String,
    endpoint: String,
}