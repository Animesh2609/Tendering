import { DEMO_MODE } from '../data/constants';
import { demoSnapshot, demoSave } from '../api/demoStore';
// Add only browser-local fixture records; no network or production data access.
export function ensurePreviewFixtures() {
  if (!DEMO_MODE) return;
  const db=demoSnapshot();
  const future=new Date(Date.now()+90*86400000).toISOString();
  if(!db.tenders.some(t=>t.id==='TND-UI-DRAFT')) db.tenders.unshift({id:'TND-UI-DRAFT',title:'Campus Learning Centre Renovation',description:'Refurbishment of study spaces, accessible entrances and interior lighting.',eligibilityCriteria:'Registered contractors with comparable institutional projects.',requiredDocuments:'Technical proposal, registration and past project references',sector:'Construction',budget:3500000,submissionDeadline:future,status:'DRAFT',createdById:'demo-lister',createdBy:'Metro Procurement Office',ledgerStatus:'DEMO_ONLY'});
  if(!db.bids.some(b=>b.id==='BID-UI-PREVIEW')) db.bids.unshift({id:'BID-UI-PREVIEW',tenderId:'TND-1001',tenderTitle:'Road Construction and Drainage',bidderId:'demo-bidder',bidderName:'ABC Constructions Ltd.',amount:4250000,proposalSummary:'Road construction, storm-water drainage and lighting delivered through staged milestones.',remarks:'Sample record for the UI preview.',proposalFileName:'sample-technical-proposal.pdf',evidenceFileName:'sample-credentials.pdf',status:'SUBMITTED',submittedAt:new Date().toISOString(),tenderDeadline:future,ledgerStatus:'DEMO_ONLY'});
  const road=db.tenders.find(t=>t.id==='TND-1001');if(road&&Date.parse(road.submissionDeadline)<Date.now())road.submissionDeadline=future;
  if(!db.tenders.some(t=>t.id==='TND-UI-HISTORY'))db.tenders.push({id:'TND-UI-HISTORY',title:'Regional Office Network Upgrade',status:'CANCELLED',assignedEvaluatorId:'demo-evaluator',createdById:'demo-lister',submissionDeadline:'2026-10-01T17:00:00Z',openingDate:'2026-10-02T09:00:00Z',budget:1200000});
  if(!db.tenders.some(t=>t.id==='TND-UI-AWARD')) {
    db.tenders.push({id:'TND-UI-AWARD',title:'Community Library Accessibility Works',status:'ON_HOLD',createdById:'demo-lister',budget:1600000});
    db.bids.push({id:'BID-UI-AWARD',tenderId:'TND-UI-AWARD',bidderId:'sample-contractor',bidderName:'Access Civil Works',amount:1480000,status:'EVALUATED',score:92,proposalFileName:'sample-proposal.pdf'});
    db.reports.push({reportId:'RPT-UI-AWARD',tenderId:'TND-UI-AWARD',tenderTitle:'Community Library Accessibility Works',bidId:'BID-UI-AWARD',type:'MISSING_BLOCKCHAIN_RECORD',source:'SYSTEM',description:'Sample review completed; a decision can now be recorded.',status:'DISMISSED',resolutionNotes:'Sample evidence reviewed.',createdAt:'2026-11-06T10:00:00Z'});
  }
  for(const u of db.users.filter(u=>['demo-bidder','demo-lister'].includes(u.id)))u.companyProfile ||= {companyName:u.organizationName,contactNumber:'+91 98765 43210',address:'Pilani, Rajasthan, India',registrationNumber:'DEMO-ORG-2026',website:'https://example.org'};
  for (const t of db.tenders.filter(t => t.status === 'AWARDED' && !t.winningBidId)) {
    const bid = db.bids.find(b => b.tenderId === t.id);
    if (bid) { t.winningBidId = bid.id; bid.status = 'SELECTED'; }
  }
  demoSave(db);
}
