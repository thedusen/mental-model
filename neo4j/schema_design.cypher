/ Create uniqueness constraints for primary keys
CREATE CONSTRAINT expert_id_unique IF NOT EXISTS FOR (e:Expert) REQUIRE e.expertId IS UNIQUE;
CREATE CONSTRAINT model_id_unique IF NOT EXISTS FOR (m:MentalModel) REQUIRE m.modelId IS UNIQUE;
CREATE CONSTRAINT principle_id_unique IF NOT EXISTS FOR (p:Principle) REQUIRE p.principleId IS UNIQUE;
CREATE CONSTRAINT pattern_id_unique IF NOT EXISTS FOR (p:Pattern) REQUIRE p.patternId IS UNIQUE;
CREATE CONSTRAINT example_id_unique IF NOT EXISTS FOR (e:Example) REQUIRE e.exampleId IS UNIQUE;

// Create indexes for faster lookups on foreign keys
CREATE INDEX model_expert_id_index IF NOT EXISTS FOR (m:MentalModel) ON (m.expertId);
CREATE INDEX principle_model_id_index IF NOT EXISTS FOR (p:Principle) ON (p.modelId);
CREATE INDEX pattern_model_id_index IF NOT EXISTS FOR (p:Pattern) ON (p.modelId);
CREATE INDEX example_model_id_index IF NOT EXISTS FOR (e:Example) ON (e.modelId);

// Optional: Create a text index for full-text search later
// CREATE FULLTEXT INDEX example_content_index IF NOT EXISTS FOR (e:Example) ON (e.content);

// Log completion
// RETURN "Schema constraints and indexes created successfully."
