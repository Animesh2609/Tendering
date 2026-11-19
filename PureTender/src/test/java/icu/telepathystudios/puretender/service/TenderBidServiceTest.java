package icu.telepathystudios.puretender.service;

import icu.telepathystudios.puretender.dto.bid.CreateBidRequest;
import icu.telepathystudios.puretender.dto.tender.CreateTenderRequest;
import icu.telepathystudios.puretender.model.classes.Bid;
import icu.telepathystudios.puretender.model.classes.Tender;
import icu.telepathystudios.puretender.model.classes.User;
import icu.telepathystudios.puretender.model.enums.AccountStatus;
import icu.telepathystudios.puretender.model.enums.BidStatus;
import icu.telepathystudios.puretender.model.enums.Role;
import icu.telepathystudios.puretender.model.enums.TenderStatus;
import icu.telepathystudios.puretender.repo.AuthRepo;
import icu.telepathystudios.puretender.repo.bid.BidDocumentRepo;
import icu.telepathystudios.puretender.repo.bid.BidRepo;
import icu.telepathystudios.puretender.repo.tender.TenderAwardRepo;
import icu.telepathystudios.puretender.repo.tender.TenderRepo;
import icu.telepathystudios.puretender.service.blockchain.BlockchainRecordService;
import icu.telepathystudios.puretender.service.blockchain.DocumentHashService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class TenderBidServiceTest {

    @Mock TenderRepo tenderRepo;
    @Mock TenderAwardRepo tenderAwardRepo;
    @Mock BidRepo bidRepo;
    @Mock AuthRepo authRepo;
    @Mock BidDocumentRepo bidDocumentRepo;
    @Mock BlockchainRecordService blockchainRecordService;
    @Mock DocumentHashService documentHashService;

    private TenderService tenderService;
    private BidService bidService;
    private Authentication authentication;
    private User authority;
    private User contractor;

    @BeforeEach
    void setUp() {
        tenderService = new TenderService(tenderRepo, tenderAwardRepo, bidRepo, authRepo, blockchainRecordService);
        bidService = new BidService(bidRepo, tenderRepo, authRepo, bidDocumentRepo,
                documentHashService, blockchainRecordService);
        authentication = mock(Authentication.class);
        authority = user(Role.AUTHORITY, AccountStatus.VERIFIED);
        contractor = user(Role.CONTRACTOR, AccountStatus.VERIFIED);
    }

    @Test
    void createTenderPersistsAndRecordsTender() {
        when(authentication.getName()).thenReturn("authority@example.com");
        when(authRepo.findByEmail("authority@example.com")).thenReturn(Optional.of(authority));
        when(authRepo.findById(authority.getId())).thenReturn(Optional.of(authority));
        when(tenderRepo.save(any(Tender.class))).thenAnswer(invocation -> {
            Tender tender = invocation.getArgument(0);
            tender.setId(UUID.randomUUID());
            return tender;
        });
        Instant deadline = Instant.now().plusSeconds(3600);
        var request = new CreateTenderRequest("Road Works", "Repair roads", new BigDecimal("1200.00"),
                deadline, deadline.plusSeconds(3600));

        var response = tenderService.createTender(authentication, request);

        assertEquals(TenderStatus.SUBMITTED, response.status());
        assertEquals(authority.getId(), response.authorityId());
        verify(blockchainRecordService).createTenderRecord(any(Tender.class));
    }

    @Test
    void createTenderRejectsDeadlineInPast() {
        when(authentication.getName()).thenReturn("authority@example.com");
        when(authRepo.findByEmail("authority@example.com")).thenReturn(Optional.of(authority));
        when(authRepo.findById(authority.getId())).thenReturn(Optional.of(authority));
        var request = new CreateTenderRequest("Road Works", "Repair roads", new BigDecimal("1200.00"),
                Instant.now().minusSeconds(30), Instant.now().plusSeconds(3600));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> tenderService.createTender(authentication, request));

        assertEquals(HttpStatus.BAD_REQUEST.value(), exception.getStatusCode().value());
        verify(tenderRepo, never()).save(any());
    }

    @Test
    void updateTenderRejectsNonSubmittedTender() {
        when(authentication.getName()).thenReturn("authority@example.com");
        when(authRepo.findByEmail("authority@example.com")).thenReturn(Optional.of(authority));
        Tender tender = tender(TenderStatus.PUBLISHED, authority);
        when(tenderRepo.findByIdAndAuthority_Id(tender.getId(), authority.getId())).thenReturn(Optional.of(tender));
        Instant deadline = Instant.now().plusSeconds(3600);
        var request = new icu.telepathystudios.puretender.dto.tender.UpdateTenderRequest(
                "Updated", "Description", new BigDecimal("100.00"), deadline, deadline.plusSeconds(600));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> tenderService.updateTender(tender.getId(), authentication, request));

        assertEquals(HttpStatus.BAD_REQUEST.value(), exception.getStatusCode().value());
        verify(tenderRepo, never()).save(any());
    }

    @Test
    void getTenderDeniesPrivateTenderToNonOwner() {
        User differentAuthority = user(Role.AUTHORITY, AccountStatus.VERIFIED);
        when(authentication.getName()).thenReturn("contractor@example.com");
        when(authRepo.findByEmail("contractor@example.com")).thenReturn(Optional.of(contractor));
        Tender tender = tender(TenderStatus.SUBMITTED, differentAuthority);
        when(tenderRepo.findById(tender.getId())).thenReturn(Optional.of(tender));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> tenderService.getTender(tender.getId(), authentication));

        assertEquals(HttpStatus.FORBIDDEN.value(), exception.getStatusCode().value());
    }

    @Test
    void cancelTenderChangesStatusAndTrimsReason() {
        when(authentication.getName()).thenReturn("authority@example.com");
        when(authRepo.findByEmail("authority@example.com")).thenReturn(Optional.of(authority));
        Tender tender = tender(TenderStatus.PUBLISHED, authority);
        when(tenderRepo.findById(tender.getId())).thenReturn(Optional.of(tender));
        var response = tenderService.cancelTender(tender.getId(),
                new icu.telepathystudios.puretender.dto.audit.CancelTenderRequest("  budget change  "), authentication);

        assertEquals(TenderStatus.CANCELLED.name(), response.status());
        assertEquals("budget change", response.cancellationReason());
        verify(tenderRepo).save(tender);
    }

    @Test
    void createBidSavesDraftForVerifiedContractor() {
        when(authentication.getName()).thenReturn("contractor@example.com");
        when(authRepo.findByEmail("contractor@example.com")).thenReturn(Optional.of(contractor));
        Tender tender = tender(TenderStatus.PUBLISHED, authority);
        tender.setSubmissionDeadline(Instant.now().plusSeconds(3600));
        when(tenderRepo.findById(tender.getId())).thenReturn(Optional.of(tender));
        when(bidRepo.existsByTender_IdAndContractor_Id(tender.getId(), contractor.getId())).thenReturn(false);
        when(bidRepo.save(any(Bid.class))).thenAnswer(invocation -> {
            Bid bid = invocation.getArgument(0);
            bid.setId(UUID.randomUUID());
            return bid;
        });
        when(bidDocumentRepo.existsByBid_Id(any())).thenReturn(false);

        var response = bidService.createBid(tender.getId(), new CreateBidRequest(new BigDecimal("50.00")), authentication);

        assertEquals(BidStatus.DRAFT, response.status());
        assertEquals(new BigDecimal("50.00"), response.quotedAmount());
    }

    @Test
    void createBidRejectsDuplicateBid() {
        when(authentication.getName()).thenReturn("contractor@example.com");
        when(authRepo.findByEmail("contractor@example.com")).thenReturn(Optional.of(contractor));
        Tender tender = tender(TenderStatus.PUBLISHED, authority);
        tender.setSubmissionDeadline(Instant.now().plusSeconds(3600));
        when(tenderRepo.findById(tender.getId())).thenReturn(Optional.of(tender));
        when(bidRepo.existsByTender_IdAndContractor_Id(tender.getId(), contractor.getId())).thenReturn(true);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> bidService.createBid(tender.getId(), new CreateBidRequest(new BigDecimal("50.00")), authentication));

        assertEquals(HttpStatus.CONFLICT.value(), exception.getStatusCode().value());
        verify(bidRepo, never()).save(any());
    }

    @Test
    void submitBidRequiresUploadedProposal() {
        when(authentication.getName()).thenReturn("contractor@example.com");
        when(authRepo.findByEmail("contractor@example.com")).thenReturn(Optional.of(contractor));
        Tender tender = tender(TenderStatus.PUBLISHED, authority);
        tender.setSubmissionDeadline(Instant.now().plusSeconds(3600));
        Bid bid = bid(tender, contractor, BidStatus.DRAFT);
        when(bidRepo.findById(bid.getId())).thenReturn(Optional.of(bid));
        when(bidDocumentRepo.existsByBid_Id(bid.getId())).thenReturn(false);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> bidService.submitBid(bid.getId(), authentication));

        assertEquals(HttpStatus.BAD_REQUEST.value(), exception.getStatusCode().value());
        verify(bidRepo, never()).save(any());
    }

    @Test
    void submitBidMarksDraftSubmittedAndWritesLedgerRecord() {
        when(authentication.getName()).thenReturn("contractor@example.com");
        when(authRepo.findByEmail("contractor@example.com")).thenReturn(Optional.of(contractor));
        Tender tender = tender(TenderStatus.PUBLISHED, authority);
        tender.setSubmissionDeadline(Instant.now().plusSeconds(3600));
        Bid bid = bid(tender, contractor, BidStatus.DRAFT);
        when(bidRepo.findById(bid.getId())).thenReturn(Optional.of(bid));
        when(bidDocumentRepo.existsByBid_Id(bid.getId())).thenReturn(true);
        when(bidRepo.save(bid)).thenReturn(bid);
        when(bidDocumentRepo.existsByBid_Id(bid.getId())).thenReturn(true);

        var response = bidService.submitBid(bid.getId(), authentication);

        assertEquals(BidStatus.SUBMITTED, response.status());
        assertNotNull(response.submittedAt());
        verify(blockchainRecordService).createBidRecord(bid);
    }

    @Test
    void updateBidRejectsBidThatIsAlreadyEvaluated() {
        when(authentication.getName()).thenReturn("contractor@example.com");
        when(authRepo.findByEmail("contractor@example.com")).thenReturn(Optional.of(contractor));
        Tender tender = tender(TenderStatus.PUBLISHED, authority);
        tender.setSubmissionDeadline(Instant.now().plusSeconds(3600));
        Bid bid = bid(tender, contractor, BidStatus.EVALUATED);
        when(bidRepo.findById(bid.getId())).thenReturn(Optional.of(bid));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> bidService.updateBid(bid.getId(),
                        new icu.telepathystudios.puretender.dto.bid.UpdateBidRequest(new BigDecimal("60.00")), authentication));

        assertEquals(HttpStatus.BAD_REQUEST.value(), exception.getStatusCode().value());
    }

    private static User user(Role role, AccountStatus status) {
        User user = new User();
        user.setId(UUID.randomUUID());
        user.setFullName(role.name() + " Person");
        user.setEmail(role.name().toLowerCase() + "@example.com");
        user.setRole(role);
        user.setStatus(status);
        return user;
    }

    private static Tender tender(TenderStatus status, User authority) {
        Tender tender = new Tender();
        tender.setId(UUID.randomUUID());
        tender.setTitle("Road Works");
        tender.setDescription("Repair roads");
        tender.setEstimatedValue(new BigDecimal("1000.00"));
        tender.setSubmissionDeadline(Instant.now().plusSeconds(3600));
        tender.setOpeningDate(Instant.now().plusSeconds(7200));
        tender.setStatus(status);
        tender.setAuthority(authority);
        return tender;
    }

    private static Bid bid(Tender tender, User contractor, BidStatus status) {
        Bid bid = new Bid();
        bid.setId(UUID.randomUUID());
        bid.setTender(tender);
        bid.setContractor(contractor);
        bid.setQuotedAmount(new BigDecimal("50.00"));
        bid.setStatus(status);
        return bid;
    }
}
