package icu.telepathystudios.puretender.service;


import icu.telepathystudios.puretender.dto.bid.BidProposalDownload;
import icu.telepathystudios.puretender.dto.bid.BidResponse;
import icu.telepathystudios.puretender.dto.bid.CreateBidRequest;
import icu.telepathystudios.puretender.dto.bid.UpdateBidRequest;
import icu.telepathystudios.puretender.model.classes.Bid;
import icu.telepathystudios.puretender.model.classes.BidDocument;
import icu.telepathystudios.puretender.model.classes.Tender;
import icu.telepathystudios.puretender.model.classes.User;
import icu.telepathystudios.puretender.model.enums.AccountStatus;
import icu.telepathystudios.puretender.model.enums.BidStatus;
import icu.telepathystudios.puretender.model.enums.Role;
import icu.telepathystudios.puretender.model.enums.TenderStatus;
import icu.telepathystudios.puretender.repo.AuthRepo;
import icu.telepathystudios.puretender.repo.bid.BidDocumentRepo;
import icu.telepathystudios.puretender.repo.bid.BidRepo;
import icu.telepathystudios.puretender.repo.tender.TenderRepo;
import icu.telepathystudios.puretender.service.blockchain.DocumentHashService;
import icu.telepathystudios.puretender.service.blockchain.BlockchainRecordService;
import lombok.RequiredArgsConstructor;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.math.RoundingMode;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class BidService {

    private final BidRepo bidRepo;
    private final TenderRepo tenderRepo;
    private final AuthRepo authRepo;
    private final BidDocumentRepo bidDocumentRepo;
    private final DocumentHashService documentHashService;
    private final BlockchainRecordService blockchainRecordService;

    //region Bid creation, editing, and submission
    // CREATE DRAFT BID
    @Transactional
    public BidResponse createBid(
            UUID tenderId,
            CreateBidRequest request,
            org.springframework.security.core.Authentication authentication
    ) {

        User contractor = getVerifiedContractor(authentication);

        Tender tender = getTender(tenderId);

        validateTenderForBidding(tender);

        if (bidRepo.existsByTender_IdAndContractor_Id(
                tenderId,
                contractor.getId()
        )) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "You have already created a bid for this tender"
            );
        }

        Bid bid = new Bid();

        bid.setTender(tender);
        bid.setContractor(contractor);
        bid.setQuotedAmount(request.quotedAmount().setScale(2, RoundingMode.UNNECESSARY));
        bid.setStatus(BidStatus.DRAFT);

        return mapToResponse(bidRepo.save(bid));
    }

    // UPDATE DRAFT OR SUBMITTED BID
    @Transactional
    public BidResponse updateBid(
            UUID bidId,
            UpdateBidRequest request,
            org.springframework.security.core.Authentication authentication
    ) {

        User contractor = getVerifiedContractor(authentication);

        Bid bid = getContractorBid(bidId, contractor.getId());

        if (!isEditableBid(bid)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Only draft or submitted bids can be updated"
            );
        }

        validateTenderForBidding(bid.getTender());

        bid.setQuotedAmount(request.quotedAmount().setScale(2, RoundingMode.UNNECESSARY));

        Bid savedBid = bidRepo.save(bid);
        if (savedBid.getStatus() == BidStatus.SUBMITTED) {
            blockchainRecordService.updateBidRecord(savedBid, null);
        }
        return mapToResponse(savedBid);
    }

    // SUBMIT BID
    @Transactional
    public BidResponse submitBid(
            UUID bidId,
            org.springframework.security.core.Authentication authentication
    ) {

        User contractor = getVerifiedContractor(authentication);

        Bid bid = getContractorBid(bidId, contractor.getId());

        if (bid.getStatus() != BidStatus.DRAFT) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Only draft bids can be submitted"
            );
        }
        if (!bidDocumentRepo.existsByBid_Id(bidId)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Upload your proposal PDF before submitting the bid"
            );
        }


        validateTenderForBidding(bid.getTender());

        bid.setStatus(BidStatus.SUBMITTED);
        bid.setSubmittedAt(Instant.now().truncatedTo(ChronoUnit.MICROS));

        Bid submittedBid = bidRepo.save(bid);
        blockchainRecordService.createBidRecord(submittedBid);
        return mapToResponse(submittedBid);
    }

    //endregion

    //region Bidder bid queries
    // GET MY BIDS
    @Transactional(readOnly = true)
    public Page<BidResponse> getMyBids(
            org.springframework.security.core.Authentication authentication,
            Pageable pageable
    ) {

        User contractor = getVerifiedContractor(authentication);

        return bidRepo.findAllByContractor_Id(
                contractor.getId(),
                pageable
        ).map(this::mapToResponse);
    }

    // GET MY BID DETAILS
    @Transactional(readOnly = true)
    public BidResponse getMyBid(
            UUID bidId,
            org.springframework.security.core.Authentication authentication
    ) {

        User contractor = getVerifiedContractor(authentication);

        Bid bid = getContractorBid(bidId, contractor.getId());

        return mapToResponse(bid);
    }

    //endregion

    //region Bidder authorization and tender validation
    // VALIDATE CONTRACTOR
    private User getVerifiedContractor(
            org.springframework.security.core.Authentication authentication
    ) {

        User contractor = authRepo
                .findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.UNAUTHORIZED,
                        "Authenticated user not found"
                ));

        if (contractor.getRole() != Role.CONTRACTOR) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "Only contractors can perform bidding operations"
            );
        }

        if (contractor.getStatus() != AccountStatus.VERIFIED) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "Your account must be verified"
            );
        }

        return contractor;
    }

    // GET TENDER
    private Tender getTender(UUID tenderId) {

        return tenderRepo.findById(tenderId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Tender not found"
                ));
    }

    // GET BID OWNED BY CONTRACTOR
    private Bid getContractorBid(
            UUID bidId,
            UUID contractorId
    ) {

        Bid bid = bidRepo.findById(bidId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Bid not found"
                ));

        if (!bid.getContractor().getId().equals(contractorId)) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "You do not own this bid"
            );
        }

        return bid;
    }

    // VALIDATE TENDER STATUS AND DEADLINE
    private void validateTenderForBidding(Tender tender) {

        if (tender.getStatus() != TenderStatus.PUBLISHED) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Bidding is not open for this tender"
            );
        }

        if (!Instant.now().isBefore(tender.getSubmissionDeadline())) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Bid submission deadline has passed"
            );
        }
    }

    private boolean isEditableBid(Bid bid) {
        return bid.getStatus() == BidStatus.DRAFT
                || bid.getStatus() == BidStatus.SUBMITTED;
    }

    //endregion

    //region Proposal upload and download
    @Transactional
    public void uploadProposal(
            UUID bidId,
            MultipartFile file,
            Authentication authentication
    ) {

        User contractor = getVerifiedContractor(authentication);

        Bid bid = getContractorBid(bidId, contractor.getId());

        if (!isEditableBid(bid)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Proposal can only be uploaded to a draft or submitted bid"
            );
        }

        validateTenderForBidding(bid.getTender());

        validatePdf(file);

        byte[] fileData;

        try {
            fileData = file.getBytes();
        } catch (IOException e) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "Could not read uploaded PDF"
            );
        }

        String hash = documentHashService.sha256(fileData);

        BidDocument document = bidDocumentRepo
                .findByBid_Id(bidId)
                .orElseGet(BidDocument::new);

        document.setBid(bid);
        document.setFileName(file.getOriginalFilename());
        document.setContentType("application/pdf");
        document.setFileData(fileData);
        document.setSha256Hash(hash);

        BidDocument savedDocument = bidDocumentRepo.save(document);
        if (bid.getStatus() == BidStatus.SUBMITTED) {
            blockchainRecordService.updateBidRecord(bid, savedDocument);
        }
    }

    @Transactional(readOnly = true)
    public BidProposalDownload downloadProposal(
            UUID bidId,
            Authentication authentication
    ) {

        User contractor = getVerifiedContractor(authentication);

        Bid bid = getContractorBid(bidId, contractor.getId());

        BidDocument document = bidDocumentRepo.findByBid_Id(bidId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Proposal PDF not found"
                ));

        verifyDocumentHash(document);

        return new BidProposalDownload(
                document.getFileData(),
                document.getFileName(),
                document.getContentType()
        );
    }

    //endregion

    //region Proposal validation and response mapping
    private void validatePdf(MultipartFile file) {

        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Proposal PDF is required"
            );
        }

        if (file.getSize() > 10 * 1024 * 1024) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "PDF size cannot exceed 10 MB"
            );
        }

        if (!"application/pdf".equalsIgnoreCase(file.getContentType())) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Only PDF files are allowed"
            );
        }

        try {
            byte[] header = file.getBytes();

            if (header.length < 5
                    || header[0] != '%'
                    || header[1] != 'P'
                    || header[2] != 'D'
                    || header[3] != 'F'
                    || header[4] != '-') {

                throw new ResponseStatusException(
                        HttpStatus.BAD_REQUEST,
                        "Uploaded file is not a valid PDF"
                );
            }

        } catch (IOException e) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Could not validate uploaded file"
            );
        }
    }
    private void verifyDocumentHash(BidDocument document) {
        if (!documentHashService.matches(
                document.getFileData(), document.getSha256Hash())) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "Stored proposal PDF failed its integrity check"
            );
        }
    }

    // ENTITY TO DTO
    private BidResponse mapToResponse(Bid bid) {

        return new BidResponse(
                bid.getId(),
                bid.getTender().getId(),
                bid.getTender().getTitle(),
                bid.getTender().getStatus(),
                bid.getContractor().getId(),
                bid.getContractor().getFullName(),
                bid.getQuotedAmount(),
                bid.getStatus(),
                bid.getSubmittedAt(),
                bid.getOpenedAt(),
                bid.getCreatedAt(),
                bid.getUpdatedAt(),
                bidDocumentRepo.existsByBid_Id(bid.getId())
        );
    }
    //endregion
}
