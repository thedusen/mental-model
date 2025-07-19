
## Project Overview & Goal
This is a Minimum Viable Product (MVP) to translate an expert's mental model into an interactive knowledge graph. The primary goal is to create a system that allows users to visualize and chat with the expert's knowledge. The graph represents the expert's patterns of thinking, feeling, and intuiting as a dynamic network of concepts and relationships.

## Technology Stack
Database: Neo4j Community Edition (run via Docker)

Backend: Python with FastAPI

Frontend: React with Neo4j NVL for visualization

LLM (Generation): Anthropic's Claude Sonnet 4 is used for chat responses and collaborative relationship creation.

LLM (Embeddings): Cohere's embed-english-v3.0 is used to generate vector embeddings for nodes.

## Graph Schema
Node Labels:

(:Theme): Represents a high-level theme derived from a chunk of the interview.

(:Entity): A generic label for all knowledge nodes.

Specific entity labels are also applied: (:Principle), (:Pattern), (:Example).

Node Properties:

id: The unique name of the entity (e.g., "Interconnected Systems Thinking"). Used for MERGE operations.

name: The human-readable name of the entity (often the same as id).

description or content: The detailed text explaining the node. This property is used for generating embeddings.

theme: The name of the Theme this entity belongs to.

source_chunk: The original JSON filename the node was extracted from.

embedding: A 1024-dimension vector from Cohere stored on all :Entity nodes.

Relationship Types:

(Entity)-[:BELONGS_TO]->(Theme): Connects a knowledge node to its parent theme.

(Entity)-[:INFLUENCES]->(Entity)

(Entity)-[:SUPPORTS]->(Entity)

(Entity)-[:CONTRADICTS]->(Entity)

(Entity)-[:DEMONSTRATES]->(Entity)

(Entity)-[:PART_OF]->(Entity)

(Entity)-[:USES]->(Entity)

(Entity)-[:LEADS_TO]->(Entity)

## Core Workflow
Data Prep: 71 JSON files are grouped into batches using create_batches.py.

Thematic Enrichment: A manual, collaborative process with an LLM assigns a "theme" to the data in each batch. The output is saved in the data/themed_json directory.

Graph Import: The import_data.py script reads the themed JSON files, creates :Entity and :Theme nodes, stores Cohere-generated embeddings on each :Entity node, and connects entities to their parent theme with a [:BELONGS_TO] relationship.

Relationship Building: A manual, collaborative process using the "Playbook" prompts is used to create meaningful relationships between the :Entity nodes.

## Guiding Philosophy
The project's philosophy is centered on capturing a "living" mental model. Key concepts are:

Organic Evolution: The graph is not static; it's designed to grow and evolve.

Systems Thinking: The focus is on the interconnectedness of ideas, not just isolated concepts.

Pattern Recognition: The goal is to map the expert's unique patterns of thought.

Simplicity & Flexibility: The technical implementation should be as simple as possible to support an organic and improvisational development process.

## Key File Structure
backend/: Contains all Python code.

config.py: Handles API keys and database connections.

create_batches.py: Groups source JSON files for theming.

import_data.py: Imports themed JSON data into Neo4j.

main.py: The FastAPI server for the chat and graph visualization APIs.

frontend/: Contains the React application for the UI.

data/themed_json/: Location of the JSON files after being processed by the LLM to add themes.

docker-compose.yml: Defines and runs the Neo4j database service.