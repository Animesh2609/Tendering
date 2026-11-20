// Matches the extended RegisterRequest.java included with backend-overlay.
// Note: role is passed in the URL (/register/CONTRACTOR or /register/AUTHORITY),
// NOT as an untrusted JSON role field.
export function toRegisterRequest(form) {
  return {
    fullName: form.fullName.trim(),
    email: form.email.trim().toLowerCase(),
    password: form.password,
    phoneNumber: (form.phoneNumber || '').trim(),
    age: form.age ? Number(form.age) : null,
    designation: (form.designation || '').trim(),
    yearsOfExperience: form.yearsOfExperience === '' ? null : Number(form.yearsOfExperience),
    organizationName: (form.organizationName || '').trim(),
    organizationType: form.organizationType,
    registrationId: (form.registrationId || '').trim(),
    industry: form.sector,
    address: (form.address || '').trim(),
  };
}
// The demo signup accepts the same visible fields as the team backend.
// Do not create fictitious age, designation, sector, or experience records.
export function toDemoRegisterRequest(form) {
  return {
    fullName: String(form.fullName ?? '').trim(),
    email: String(form.email ?? '').trim().toLowerCase(),
    password: form.password,
    role: form.role,
    organizationName: String(form.organizationName ?? '').trim(),
    address: String(form.address ?? '').trim(),
    phoneNumber: String(form.phoneNumber ?? '').trim(),
    registrationId: String(form.registrationId ?? '').trim(),
  };
}

export function toLoginRequest(form) {
  return { email: form.email.trim().toLowerCase(), password: form.password };
}
export function normalizeRole(value) {
  // Older TenderBlock draft used CONTRACTOR/AUTHORITY; new whiteboard uses BIDDER/LISTER.
  const upper = String(value || '').toUpperCase();
  if (upper === 'CONTRACTOR') return 'BIDDER';
  if (upper === 'AUTHORITY') return 'LISTER';
  return upper;
}
export function toCurrentUser(raw) {
  const source = raw?.user || raw;
  return {
    id: source?.id ?? source?.userId ?? source?.email,
    fullName: source?.fullName ?? source?.name ?? 'Account',
    email: source?.email ?? '',
    phoneNumber: source?.phoneNumber ?? '',
    designation: source?.designation ?? '',
    yearsOfExperience: source?.yearsOfExperience ?? null,
    organizationName: source?.organizationName ?? source?.organization?.name ?? '',
    sector: source?.industry ?? source?.sector ?? '',
    accountStatus: source?.accountStatus ?? null,
    verified: source?.verified ?? (source?.accountStatus ? source.accountStatus === 'VERIFIED' : false),
    role: normalizeRole(source?.role),
  };
}
export function toTenderCreateRequest(form) {
  return {
    title: form.title.trim(), description: form.description.trim(),
    sector: form.sector, department: form.department.trim(),
    budget: Number(form.budget), submissionDeadline: new Date(form.submissionDeadline).toISOString(),
    eligibilityCriteria: form.eligibilityCriteria.trim(),
    requiredDocuments: form.requiredDocuments.trim(),
  };
}
export function normalizeTender(raw) {
  return {
    ...raw,
    id: raw?.id ?? raw?.tenderId,
    sector: raw?.sector ?? raw?.category ?? raw?.industry ?? null,
    department: raw?.department ?? raw?.authorityName ?? raw?.organizationName ?? raw?.createdBy ?? 'Tender issuer',
    budget: raw?.budget ?? raw?.estimatedValue,
    submissionDeadline: raw?.submissionDeadline ?? raw?.deadline,
    rejectionReason: raw?.rejectionReason ?? raw?.rejection_reason ?? null,
    status: String(raw?.status ?? 'DRAFT').toUpperCase(),
  };
}
export function normalizeTenderList(response) {
  const items = Array.isArray(response) ? response : (response?.content ?? response?.items ?? response?.tenders ?? []);
  return items.map(normalizeTender);
}

// Team BidResponse: id, tenderId, tenderTitle, contractorId, contractorName,
// quotedAmount, status, submittedAt, openedAt, createdAt, updatedAt, proposalUploaded.
export function normalizeBid(raw) {
  return {
    ...raw,
    id: raw?.id ?? raw?.bidId,
    tenderId: raw?.tenderId,
    tenderTitle: raw?.tenderTitle || '',
    amount: raw?.amount ?? raw?.quotedAmount,
    quotedAmount: raw?.quotedAmount ?? raw?.amount,
    status: String(raw?.status || 'DRAFT').toUpperCase(),
    proposalUploaded: Boolean(raw?.proposalUploaded),
  };
}
export function normalizeBidList(raw) {
  const entries = Array.isArray(raw) ? raw : (raw?.content ?? raw?.items ?? []);
  return entries.map(normalizeBid);
}
