# ☕ AI Java Migration Assistant

> **AI-powered Java project modernization — automated migration assessment, intelligent dependency analysis, Java 21 upgrade planning, and source code refactoring.**

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Java](https://img.shields.io/badge/Java-11%2B-ED8B00?style=for-the-badge&logo=openjdk&logoColor=white)
![Java 21](https://img.shields.io/badge/Target-Java%2021-ED8B00?style=for-the-badge&logo=openjdk&logoColor=white)
![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.3.4-6DB33F?style=for-the-badge&logo=springboot&logoColor=white)
![Maven](https://img.shields.io/badge/Maven-Central-C71A36?style=for-the-badge&logo=apachemaven&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>

---

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)


---

## 🔍 Overview

### The Problem

Migrating a Java project from Java 11 to Java 21 is not a one-line version bump. It is weeks of manual work:

- Hundreds of `javax.*` imports need renaming to `jakarta.*`
- Spring Boot 2.x APIs are incompatible with Spring Boot 3.x
- `WebSecurityConfigurerAdapter` was removed entirely in Spring Security 6
- JUnit 4 annotations break under JUnit 5
- Dozens of Maven dependencies need version upgrades — each requiring manual research
- Build plugins need reconfiguration for the modern `<release>` compiler flag
- Every change carries risk of breaking the application silently

For enterprise codebases with hundreds of Java files and dozens of dependencies, this process takes experienced engineers days or weeks — and is still error-prone.

### The Solution

**AI Java Migration Assistant** automates the entire assessment and migration pipeline. Drop in a ZIP of any Maven or Gradle project and get back:

- A **full migration assessment** with risk scoring, dependency analysis, and code refactoring signals
- An **automatically updated `pom.xml`** with every dependency version resolved live from Maven Central
- **Refactored Java source files** with 26 transformation rules applied precisely and safely
- A **detailed HTML Migration Change Report** showing every file changed, every rule applied, and every version bumped — with full audit trail

No manual research. No missed imports. No forgotten dependency upgrades. Every change is documented.

### Who Is This For

| Audience | Value |
|---|---|
| **Java Developers** | Automate the mechanical parts of a Java 21 upgrade |
| **Tech Leads** | Assess migration complexity before committing to a sprint |
| **Enterprise Teams** | Migrate multiple projects consistently with full audit reports |
| **Hackathon Judges** | End-to-end migration pipeline with live API and HTML dashboards |

---

## ✅ Features

| Feature | Status | Description |
|---|---|---|
| 📦 **Project ZIP Upload** | ✅ Implemented | Upload any Maven or Gradle project as a `.zip` file |
| 🔍 **Java Project Validation** | ✅ Implemented | Validates ZIP structure, magic bytes, and build file presence |
| ☕ **Java Version Detection** | ✅ Implemented | Detects Java version from `pom.xml` properties and compiler plugin |
| 🔨 **Maven & Gradle Detection** | ✅ Implemented | Supports both `pom.xml` and `build.gradle` / `build.gradle.kts` |
| 🛡️ **Java Version Gate** | ✅ Implemented | Rejects projects below Java 11 with a clear error message |
| 📊 **Full Migration Assessment** | ✅ Implemented | 9-section analysis: deps, Java, Spring Boot, code, plugins, DB, Docker |
| 🔗 **Dynamic Dependency Resolution** | ✅ Implemented | Queries Maven Central live for every dependency and plugin version |
| 📝 **pom.xml Auto-Update** | ✅ Implemented | Updates Java version, Spring Boot parent, all plugins and dependencies |
| ♻️ **Java Source Refactoring** | ✅ Implemented | 26 transformation rules applied to all `.java` files |
| 🏷️ **javax → jakarta Migration** | ✅ Implemented | All 9 Jakarta EE namespaces migrated automatically |
| 🔐 **Spring Security 6 Migration** | ✅ Implemented | Removes `WebSecurityConfigurerAdapter`, adds `@Configuration` |
| 🧪 **JUnit 4 → JUnit 5** | ✅ Implemented | All annotations, imports, and `Assert.*` → `Assertions.*` |
| 💾 **Pre-Migration Backup** | ✅ Implemented | Full `shutil.copytree` backup before any file is modified |
| 📄 **HTML Assessment Report** | ✅ Implemented | 9-section interactive report with collapsible sections |
| 📋 **HTML Migration Change Report** | ✅ Implemented | Per-file and per-category breakdown of every change made |
| 🗄️ **Database Driver Detection** | ✅ Implemented | Detects PostgreSQL, MySQL, Oracle, SQL Server, H2, MongoDB |
| 🐳 **Docker Readiness Check** | ✅ Implemented | Detects `Dockerfile` and `docker-compose.yml`, generates recommendations |
| 🧹 **Workspace Management** | ✅ Implemented | UUID-isolated workspaces, safe deletion with path-traversal protection |
| 🏥 **Health Check** | ✅ Implemented | `GET /health` liveness endpoint |

---

## 🏗️ Architecture

