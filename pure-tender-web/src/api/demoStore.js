// Local-only reference implementation for teaching and UI testing.
// SECURITY: localStorage is editable by the visitor. This is NOT authorization,
// secure document storage, a blockchain ledger or an authentication backend.
import { SAMPLE_TENDERS } from '../data/sampleTenders';
import { normalizeRole } from './dtos';
import { demoTenders as evaluationTenders, demoBids as evaluationBids } from '../modules/evaluator/data/demoData';
import { demoTenders as pendingTenders, demoReports as seedReports, demoAuditDetails } from '../modules/operations/data/demoData';
const KEY = 'pure_tender_demo_v1';
export const DEMO_PASSWORD = 'Demo@12345';
const SEED_USERS = [
  {id:'demo-bidder', fullName:'ABC Constructions', email:'bidder@demo.test', role:'BIDDER', organizationName:'ABC Constructions Ltd.', sector:'Infrastructure', verified:true},
  {id:'demo-lister', fullName:'Metro Procurement Office', email:'lister@demo.test', role:'LISTER', organizationName:'Metro Procurement Office', sector:'Infrastructure', verified:true},
  {id:'demo-admin', fullName:'TenderBlock Admin', email:'admin@demo.test', role:'ADMIN', organizationName:'TenderBlock Administration', verified:true},
  {id:'demo-evaluator', fullName:'Technical Evaluator', email:'evaluator@demo.test', role:'EVALUATOR', organizationName:'Evaluation Board', verified:true},
  {id:'demo-auditor', fullName:'Independent Auditor', email:'auditor@demo.test', role:'AUDITOR', organizationName:'Audit Office', verified:true},
];
function load() {
  let parsed;
  try { parsed = JSON.parse(localStorage.getItem(KEY)); } catch { /* empty */ }
  return parsed && Array.isArray(parsed.users) ? parsed : {
    users: [...SEED_USERS.map(x=>({...x})), {id:'demo-pending',fullName:'New Bidder',email:'new@demo.test',role:'BIDDER',verified:false}],
    reports: structuredClone(seedReports), evaluations: {},
    tenders: [
      ...pendingTenders.map(t=>({...t,budget:t.estimatedValue,createdBy:t.authorityName,createdById:'demo-lister'})),
      ...evaluationTenders.map(t=>({...t,id:t.tenderId,budget:5000000,createdById:'demo-lister',assignedEvaluatorId:'demo-evaluator'})),
      ...Object.values(demoAuditDetails).map(t=>({...t,id:t.tenderId,title:t.tenderTitle,createdById:'demo-lister',assignedAuditorId:'demo-auditor'})),
      ...SAMPLE_TENDERS.map(x=>({...x, ledgerStatus:'DEMO_REFERENCE_ONLY'})),{
      id:'TND-ARCHIVE',title:'Demo archived tender for evaluation',department:'Campus Procurement Office',
      sector:'Office Supplies',budget:150000,submissionDeadline:'2026-10-15T17:00:00',
      status:'PUBLISHED',description:'DEMO RECORD: An expired tender used to test closing, scoring and auditing.',
      eligibilityCriteria:'Valid registration',requiredDocuments:'Proposal PDF and evidence PDF',
      createdById:'demo-lister',createdBy:'Metro Procurement Office',assignedAuditorId:'demo-auditor',ledgerStatus:'DEMO_ONLY',
    }],
    bids: [
      ...Object.values(evaluationBids).flat().map(b=>({...b,id:b.bidId,bidderName:b.contractorName,amount:b.quotedAmount,bidderId:'demo-bidder',proposalFileName:'demo-proposal.pdf'})),
      ...Object.values(demoAuditDetails).flatMap(t=>t.bids.map(b=>({...b,id:b.bidId,tenderId:t.tenderId,bidderId:b.bidderId,amount:100000,proposalFileName:'demo-proposal.pdf'}))),
      {id:'BID-ARCHIVE',tenderId:'TND-ARCHIVE',bidderId:'demo-bidder',bidderName:'ABC Constructions Ltd.',amount:135000,
      proposalSummary:'Sample historical quotation for training',remarks:'Demo-only record',evidenceFileName:'historic-evidence.pdf',
      proposalFileName:'historic-proposal.pdf',evidenceHash:null,proposalHash:null,status:'SUBMITTED',ledgerStatus:'DEMO_ONLY',
      tenderDeadline:'2026-10-15T17:00:00',submittedAt:'2026-10-14T10:00:00',updatedAt:'2026-10-14T10:00:00',score:null}], events: [],
  };
}
function save(data) { localStorage.setItem(KEY, JSON.stringify(data)); }
function snapshot() { return load(); }
function now() { return new Date().toISOString(); }
function unique(prefix) { return `${prefix}-${crypto.randomUUID().slice(0,8)}`; }
function requireRole(user, ...roles) { if (!user || !roles.includes(normalizeRole(user.role))) throw new Error('Your account does not have permission to perform this operation.'); }
function requireVerified(user, db) { const account=db.users.find(x=>x.id===user.id); if (!account?.verified) throw new Error('Admin must verify your account before this action is enabled.'); }
function log(db, actor, type, entityType, entityId, details='') {
  db.events.unshift({id:unique('EVT'), actorId:actor.id, actorName:actor.fullName, type, entityType, entityId, details, at:now(), ledgerStatus:'DEMO_ONLY'});
}
function publicAccount(acc) {const { passwordDigest:_secret, ...safe}=acc; void _secret; return {...safe, accountStatus: safe.accountStatus || (safe.verified ? 'VERIFIED' : 'PENDING')};}
function cleanTender(t) {return {...t, effectiveStatus:t.status==='PUBLISHED' && Date.parse(t.submissionDeadline)<=Date.now()?'DEADLINE_PASSED':t.status};}
function mustTender(db,id) {const t=db.tenders.find(x=>String(x.id)===String(id));if(!t)throw new Error('Tender does not exist.');return t;}
function mustBid(db,id) {const bid=db.bids.find(x=>String(x.id)===String(id));if(!bid)throw new Error('Bid not found.');return bid;}
async function sha256(input) { const bytes= typeof input==='string'?new TextEncoder().encode(input):input; const d=await crypto.subtle.digest('SHA-256',bytes);return [...new Uint8Array(d)].map(x=>x.toString(16).padStart(2,'0')).join(''); }
export async function digestFile(file) {return file ? sha256(await file.arrayBuffer()) : null;}
export function demoReset() {localStorage.removeItem(KEY);}
export function demoUsers() {return snapshot().users.map(publicAccount);}
export async function demoRegister(dto) {
  requireRole(dto,'BIDDER','LISTER','EVALUATOR');
  const db=load(); const email=dto.email.trim().toLowerCase();
  if(db.users.some(x=>x.email===email))throw new Error('An account with this email already exists.');
  const user={...dto,id:unique('USER'),email,role:dto.role,verified:false,
    passwordDigest:await sha256(dto.password)};
  delete user.password; save({...db,users:[...db.users,user]});
  return {userId:user.id,role:user.role,status:'PENDING_VERIFICATION'};
}
export async function demoLogin(dto) {
  const db=load();const account=db.users.find(x=>x.email===dto.email.trim().toLowerCase());
  if(!account) throw new Error('Invalid email or password.');
  const valid=SEED_USERS.some(x=>x.id===account.id) ? dto.password===DEMO_PASSWORD : await sha256(dto.password)===account.passwordDigest;
  if(!valid)throw new Error('Invalid email or password.');
  if (['REJECTED','DISABLED'].includes(account.accountStatus)) throw new Error('This account is rejected or disabled.');
  return {accessToken:'DEMO_TOKEN_NOT_FOR_PRODUCTION',user:publicAccount(account)};
}
export function demoGetTenders() {return snapshot().tenders.filter(t=>t.status==='PUBLISHED').map(cleanTender);}
export function demoGetTender(id) {return snapshot().tenders.find(t=>String(t.id)===String(id))||null;}
export function demoMyTenders(user) {requireRole(user,'LISTER');return snapshot().tenders.filter(t=>t.createdById===user.id).map(cleanTender);}
export function demoTenderAward(user,id) {
  requireRole(user,'LISTER');
  const db=snapshot(),tender=mustTender(db,id);
  if(tender.createdById!==user.id)throw new Error('Only the tender authority can view its award.');
  if(tender.status!=='AWARDED'||!tender.winningBidId)throw new Error('No award has been recorded for this tender.');
  const bid=mustBid(db,tender.winningBidId);
  return {tenderId:tender.id,tenderTitle:tender.title,winningBidId:bid.id,winningContractorName:bid.bidderName||bid.contractorName||'Awarded bidder',winningBidAmount:bid.amount??bid.quotedAmount,awardedAt:tender.awardedAt||null};
}
export function demoCreateTender(user,dto) {
  requireRole(user,'LISTER');const db=load();requireVerified(user,db);
  const t={...dto,id:unique('TND'),status:'DRAFT',createdById:user.id,createdBy:user.organizationName||user.fullName,
    createdAt:now(),ledgerStatus:'NOT_SUBMITTED',assignedAuditorId:null};
  db.tenders.unshift(t);log(db,user,'TENDER_CREATED','TENDER',t.id);save(db);return t;
}
export function demoUpdateTender(user,id,dto) {
  requireRole(user,'LISTER');const db=load(),t=mustTender(db,id);requireVerified(user,db);
  if(t.createdById!==user.id||t.status!=='DRAFT')throw new Error('Only your own draft tenders can be edited.');
  if(Date.parse(dto.submissionDeadline)<=Date.now())throw new Error('Deadline must be in the future.');
  Object.assign(t,dto,{updatedAt:now()});log(db,user,'TENDER_UPDATED','TENDER',t.id);save(db);return t;
}
export function demoRequestApproval(user,id) {
  requireRole(user,'LISTER');const db=load(),t=mustTender(db,id);requireVerified(user,db);
  if(t.createdById!==user.id||t.status!=='DRAFT')throw new Error('Only your own draft tenders can be sent for approval.');
  t.status='PENDING_APPROVAL';log(db,user,'APPROVAL_REQUESTED','TENDER',id);save(db);return t;
}
export function demoCancelTender(user, id, reason) {
  requireRole(user, 'LISTER');
  const db = load();
  requireVerified(user, db);
  const tender = mustTender(db, id);
  if (tender.createdById !== user.id) throw new Error('Only the tender owner may cancel it.');
  if (tender.status !== 'PUBLISHED' || Date.parse(tender.submissionDeadline) <= Date.now()) {
    throw new Error('Only your published tenders can be cancelled before the deadline.');
  }
  if (!reason?.trim() || reason.length > 2000) throw new Error('Enter a cancellation reason (maximum 2000 characters).');
  tender.status = 'CANCELLED';
  tender.cancellationReason = reason.trim();
  tender.cancelledAt = now();
  log(db, user, 'TENDER_CANCELLED', 'TENDER', id, tender.cancellationReason);
  save(db);
  return cleanTender(tender);
}
export function demoAdminQueue(user) {requireRole(user,'ADMIN');const db=load();return {users:db.users.filter(x=>!x.verified).map(publicAccount),tenders:db.tenders.filter(x=>x.status==='PENDING_APPROVAL')};}
export function demoVerifyUser(admin,userId) {
  requireRole(admin,'ADMIN');const db=load(),target=db.users.find(x=>x.id===userId);if(!target)throw new Error('User not found.');
  target.verified=true;log(db,admin,'USER_VERIFIED','USER',userId);save(db);return publicAccount(target);
}
export async function demoApproveTender(admin,id,auditorId) {
  requireRole(admin,'ADMIN');const db=load(),t=mustTender(db,id);const auditor=db.users.find(x=>x.id===auditorId&&x.role==='AUDITOR');
  if(!auditor)throw new Error('Select a valid Auditor before approval.');
  if(t.status!=='PENDING_APPROVAL')throw new Error('Only pending tenders can be approved.');
  t.status='PUBLISHED';t.publishedAt=now();t.assignedAuditorId=auditor.id;
  // Hash stored in the local demo only; does NOT submit to Hyperledger Fabric.
  t.demoTenderHash=await sha256(JSON.stringify({id:t.id,title:t.title,description:t.description,submissionDeadline:t.submissionDeadline}));
  t.ledgerStatus='DEMO_ONLY';log(db,admin,'TENDER_APPROVED','TENDER',id,'Assigned auditor: '+auditor.fullName);save(db);return t;
}
export function demoCloseTender(admin,id) {
  requireRole(admin,'ADMIN');const db=load(),t=mustTender(db,id);
  if(t.status!=='PUBLISHED')throw new Error('Only published tenders can be closed.');
  if(Date.parse(t.submissionDeadline)>Date.now())throw new Error('Tender can only be closed after its deadline.');
  t.status='UNDER_EVALUATION';t.closedAt=now();log(db,admin,'TENDER_CLOSED','TENDER',id);save(db);return t;
}
export async function demoSubmitBid(user,tenderId,form) {
  requireRole(user,'BIDDER');const db=load(),t=mustTender(db,tenderId);requireVerified(user,db);
  if(t.status!=='PUBLISHED'||Date.parse(t.submissionDeadline)<=Date.now())throw new Error('Tender is closed or deadline has passed.');
  if(db.bids.some(b=>b.bidderId===user.id&&b.tenderId===tenderId))throw new Error('You already have a bid. Edit it in My Bids before the deadline.');
  const bid={id:unique('BID'),tenderId,bidderId:user.id,bidderName:user.organizationName||user.fullName,
    amount:Number(form.amount),proposalSummary:form.proposalSummary.trim(),remarks:(form.remarks||'').trim(),
    evidenceFileName:form.evidence?.name||'',proposalFileName:form.proposal?.name||'',
    evidenceHash:await digestFile(form.evidence),proposalHash:await digestFile(form.proposal),
    status:'SUBMITTED',ledgerStatus:'DEMO_ONLY',tenderDeadline:t.submissionDeadline,submittedAt:now(),updatedAt:now(),score:null};
  if(!(bid.amount>0)||!bid.proposalSummary||!bid.evidenceHash||!bid.proposalHash)throw new Error('Amount, summary and both evidence PDFs are required.');
  db.bids.unshift(bid);log(db,user,'BID_SUBMITTED','BID',bid.id,'Demo hashes calculated; no ledger transaction');save(db);return bid;
}
export async function demoUpdateBid(user,bidId,form) {
  requireRole(user,'BIDDER');const db=load(),bid=mustBid(db,bidId),t=mustTender(db,bid.tenderId);requireVerified(user,db);
  if(bid.bidderId!==user.id||bid.status!=='SUBMITTED')throw new Error('Only your submitted bid can be edited.');
  if(t.status!=='PUBLISHED'||Date.parse(t.submissionDeadline)<=Date.now())throw new Error('Bid editing deadline has passed.');
  const update={amount:Number(form.amount),proposalSummary:form.proposalSummary.trim(),remarks:(form.remarks||'').trim()};
  if(!(update.amount>0)||!update.proposalSummary)throw new Error('Provide a valid amount and proposal summary.');
  Object.assign(bid,update,{updatedAt:now()});
  if(form.evidence){bid.evidenceHash=await digestFile(form.evidence);bid.evidenceFileName=form.evidence.name;}
  if(form.proposal){bid.proposalHash=await digestFile(form.proposal);bid.proposalFileName=form.proposal.name;}
  bid.ledgerStatus='DEMO_ONLY';log(db,user,'BID_UPDATED','BID',bid.id,'Updated before deadline');save(db);return bid;
}
export function demoMyBids(user) {requireRole(user,'BIDDER');return snapshot().bids.filter(b=>b.bidderId===user.id);}
export function demoEvaluationQueue(user) {requireRole(user,'EVALUATOR');const db=load();return db.tenders.filter(t=>t.status==='UNDER_EVALUATION').map(t=>({tender:t,bids:db.bids.filter(b=>b.tenderId===t.id)}));}
export function demoEvaluateBid(user,bidId,score,remarks) {
  requireRole(user,'EVALUATOR');const db=load(),bid=mustBid(db,bidId),t=mustTender(db,bid.tenderId);
  if(t.status!=='UNDER_EVALUATION')throw new Error('Evaluation is permitted only after tender closing.');
  if(!Number.isFinite(Number(score))||Number(score)<0||Number(score)>100)throw new Error('Score must be from 0 to 100.');
  bid.score=Number(score);bid.evaluationRemarks=remarks||'';bid.evaluatorId=user.id;bid.evaluatedAt=now();bid.status='EVALUATED';
  log(db,user,'BID_EVALUATED','BID',bid.id,`Score: ${bid.score}`);save(db);return bid;
}
export function demoAuditQueue(user) {requireRole(user,'AUDITOR');const db=load();return db.tenders.filter(t=>t.assignedAuditorId===user.id).map(t=>({tender:t,bids:db.bids.filter(b=>b.tenderId===t.id)}));}
export async function demoVerifyBidFile(user,bidId,file,kind='proposal') {
  requireRole(user,'AUDITOR');const db=load(),bid=mustBid(db,bidId),t=mustTender(db,bid.tenderId);
  if(t.assignedAuditorId!==user.id)throw new Error('You are not assigned to this tender.');
  if(!file)throw new Error('Choose a PDF to compare.');
  if(!file.name.toLowerCase().endsWith('.pdf') || file.size>10*1024*1024)throw new Error('Choose a PDF under 10 MB.');
  if(!bid[kind==='evidence'?'evidenceHash':'proposalHash']) throw new Error('This historical demo record has no original document hash. Upload a new bid to test a matching hash.');
  const hash=await digestFile(file);const expected=kind==='evidence'?bid.evidenceHash:bid.proposalHash;
  const matches=hash===expected;
  if(!bid.auditChecks)bid.auditChecks={};bid.auditChecks[kind]={matches,checkedAt:now(),checkedBy:user.id,hash};
  if(!matches) {bid.flagged=true;log(db,user,'BID_HASH_MISMATCH','BID',bid.id,kind);} else log(db,user,'BID_HASH_MATCH','BID',bid.id,kind);
  save(db);return {matches,expected,actual:hash,status:'DEMO_LOCAL_HASH_COMPARISON'};
}
export function demoAuditEvents(user,tenderId) {
  requireRole(user,'AUDITOR','ADMIN');const db=load();
  if(user.role==='AUDITOR' && !db.tenders.some(t=>t.id===tenderId&&t.assignedAuditorId===user.id))throw new Error('You are not assigned to this tender.');
  return db.events.filter(e=>e.entityId===tenderId||db.bids.some(b=>b.tenderId===tenderId&&b.id===e.entityId));
}
export function demoFinalizeTender(admin,id) {
  requireRole(admin,'ADMIN');const db=load(),t=mustTender(db,id);
  if(t.status!=='UNDER_EVALUATION')throw new Error('Tender must be in evaluation stage.');
  const bids=db.bids.filter(x=>x.tenderId===id);if(!bids.length)throw new Error('No bids submitted.');
  if(bids.some(b=>b.status!=='EVALUATED'))throw new Error('All bids must receive evaluator scores.');
  if(bids.some(b=>b.flagged)) {t.status='FLAGGED';log(db,admin,'TENDER_FLAGGED','TENDER',id,'Document mismatch detected');}
  else {t.status='AWARDED';t.winningBidId=[...bids].sort((a,b)=>b.score-a.score)[0].id;log(db,admin,'TENDER_AWARDED','TENDER',id,'Demo award only');}
  t.ledgerStatus='DEMO_ONLY';save(db);return t;
}
export function demoAllReviewTenders(user) {requireRole(user,'ADMIN');return snapshot().tenders.filter(t=>['PUBLISHED','UNDER_EVALUATION','FLAGGED','AWARDED'].includes(t.status));}

// Shared persistence hooks for the integrated staff demo adapters.
export const demoSnapshot = snapshot;
export const demoSave = save;
