// Manual Seed Data for Validation

// Create the Expert and their Mental Model
MERGE (e:Expert {expertId: 'dan-hackett', name: 'Dan Hackett'})
MERGE (m:MentalModel {modelId: 'profit-architect', name: 'Profit Architect', expertId: 'dan-hackett', description: 'A framework for building profitable businesses.'})
MERGE (e)-[:OWNS]->(m);

// Create a Principle
MERGE (p1:Principle {
  principleId: 'p001',
  name: 'Constraint as a Lens',
  description: 'Using limitations not as barriers, but as focusing mechanisms to reveal the most critical path.',
  category: 'Decision Architecture',
  energy_tag: 'energizing',
  modelId: 'profit-architect'
})
MERGE (m)-[:DEFINED_BY]->(p1);

// Create a Pattern that manifests the Principle
MERGE (pat1:Pattern {
  patternId: 'pat001',
  name: 'The 5-Day Scope',
  description: 'For any new initiative, define what can be built and tested in 5 days. This forces clarity.',
  context: 'Early-stage product development and feature validation.',
  modelId: 'profit-architect'
})
MERGE (p1)-[:MANIFESTS_AS]->(pat1);

// Create an Example that illustrates the Pattern
MERGE (ex1:Example {
  exampleId: 'ex001',
  name: 'The SaaS Onboarding Test',
  content: 'We had a huge roadmap, but we asked, "What can we ship in one week?" The answer was a simple email onboarding sequence. It ended up being our highest converting channel.',
  source: 'Interview 2, Transcript.md',
  timestamp: '00:45:12',
  modelId: 'profit-architect'
})
MERGE (pat1)-[:ILLUSTRATED_BY]->(ex1);
MERGE (pat1)-[:SUPPORTED_BY]->(ex1); // An example can also be the supporting quote
