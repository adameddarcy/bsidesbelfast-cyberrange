-- Cyber Range — MySQL init script
-- Creates mock "sensitive records" table alongside Juice Shop schema.
-- Participants discovering SQLi in Juice Shop can pivot to this data.

-- [VULN] All data inserted by root with no row-level security

CREATE DATABASE IF NOT EXISTS rangecorp;
USE rangecorp;

CREATE TABLE employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    role VARCHAR(50),
    salary DECIMAL(10,2),
    api_key VARCHAR(64)          -- [VULN] secrets stored in plain text
);

INSERT INTO employees (name, email, role, salary, api_key) VALUES
  ('Alice Byrne',   'alice@rangecorp.local',  'CISO',            120000, 'rng-key-a1b2c3d4e5f6g7h8'),
  ('Bob Tierney',   'bob@rangecorp.local',    'SRE Lead',         95000, 'rng-key-z9y8x7w6v5u4t3s2'),
  ('Carol Dempsey', 'carol@rangecorp.local',  'Security Analyst', 80000, 'rng-key-q1w2e3r4t5y6u7i8');

CREATE TABLE agent_audit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT NOW(),
    invoked_by VARCHAR(100),
    tool_called VARCHAR(100),
    payload TEXT,                -- [VULN] full payload logged — may include PII
    approved TINYINT(1) DEFAULT 0
);

-- Seed one unapproved agent write to illustrate missing approval workflow
INSERT INTO agent_audit (invoked_by, tool_called, payload, approved) VALUES
  ('agent-service', 'write_record', '{"table":"employees","data":{"name":"Attacker","role":"admin"}}', 0);
