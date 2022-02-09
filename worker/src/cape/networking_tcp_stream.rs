use async_trait::async_trait;
use moose::{
    computation::{RendezvousKey, SessionId, Value},
    execution::Identity,
    networking::AsyncNetworking,
};
use std::collections::HashMap;
use std::io::prelude::*;
use std::net::{TcpListener, TcpStream};
use std::sync::Arc;

pub struct TcpStreamNetworking {
    own_name: String,
    hosts: HashMap<String, String>,
    store: Arc<dashmap::DashMap<String, Arc<async_cell::sync::AsyncCell<Value>>>>,
    streams: HashMap<String, TcpStream>,
}

fn u64_to_little_endian(n: u64, buf: &mut [u8; 8]) -> anyhow::Result<()> {
    let mut n_mut = n;
    for i in 0..=7 {
        buf[i] = (n_mut & 0xff) as u8;
        n_mut >>= 8;
    }
    Ok(())
}

fn little_endian_to_u64(buf: &[u8; 8]) -> u64 {
    let mut n: u64 = 0;
    for i in 0..=7 {
        n |= (buf[i] as u64) << (i * 8);
    }
    n
}

fn handle_connection(mut stream: TcpStream) -> anyhow::Result<()> {
    loop {
        let mut buf: [u8; 8] = [0; 8];
        let size = match stream.read_exact(&mut buf) {
            Ok(_) => little_endian_to_u64(&buf),
            Err(_) => return Ok(()), // when client hangs up
        };
        let mut vec: Vec<u8> = Vec::with_capacity(size as usize);
        unsafe {
            // https://stackoverflow.com/a/28209155
            vec.set_len(size as usize);
        }

        stream.read_exact(&mut vec)?;
        let value: Value = bincode::deserialize(&vec)
            .map_err(|e| anyhow::anyhow!("failed to deserialize moose value: {}", e))?;
        println!("got moose value: {:?}", value);
        // TODO: put value into store
    }
}

fn server(listener: TcpListener) -> anyhow::Result<()> {
    loop {
        let (stream, _addr) = listener.accept().unwrap();
        tokio::spawn(async move {
            handle_connection(stream).unwrap();
        });
    }
}

impl TcpStreamNetworking {
    pub fn new(own_name: &str, hosts: HashMap<String, String>) -> TcpStreamNetworking {
        let store =
            Arc::<dashmap::DashMap<String, Arc<async_cell::sync::AsyncCell<Value>>>>::default();
        let own_name: String = own_name.to_string();
        let streams = HashMap::new();
        TcpStreamNetworking {
            own_name,
            hosts,
            store,
            streams,
        }
    }

    pub async fn init(&mut self) -> anyhow::Result<()> {
        let own_address = self
            .hosts
            .get(&self.own_name)
            .ok_or_else(|| anyhow::anyhow!("own host name not in hosts map"))?;

        // spawn the server
        println!("spawned server on: {}", own_address);
        let listener = TcpListener::bind(&own_address)?;
        tokio::spawn(async move {
            server(listener).unwrap();
        });

        // connect to every other server
        let mut others: Vec<(String, String)> = self
            .hosts
            .clone()
            .into_iter()
            .filter(|(placement, _)| *placement != self.own_name)
            .collect();
        others.sort();
        println!("others = {:?}", others);
        for (placement, address) in others.iter() {
            println!("trying: {} -> {}", placement, address);
            loop {
                let stream = match TcpStream::connect(address) {
                    Ok(s) => s,
                    Err(_) => {
                        tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
                        continue;
                    }
                };
                println!("connected to: {} -> {}", placement, address);
                self.streams.insert(placement.clone(), stream);
                break;
            }
        }

        Ok(())
    }
}

#[async_trait]
impl AsyncNetworking for TcpStreamNetworking {
    async fn send(
        &self,
        _value: &Value,
        _receiver: &Identity,
        _rendezvous_key: &RendezvousKey,
        _session_id: &SessionId,
    ) -> moose::error::Result<()> {
        unimplemented!("network stub")
    }

    async fn receive(
        &self,
        _sender: &Identity,
        _rendezvous_key: &RendezvousKey,
        _session_id: &SessionId,
    ) -> moose::error::Result<Value> {
        unimplemented!("network stub")
    }
}