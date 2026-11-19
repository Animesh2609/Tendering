package icu.telepathystudios.puretender.service.blockchain;

import icu.telepathystudios.puretender.model.classes.Bid;
import icu.telepathystudios.puretender.model.classes.BidDocument;
import icu.telepathystudios.puretender.model.classes.Tender;
import icu.telepathystudios.puretender.model.classes.User;
import icu.telepathystudios.puretender.model.enums.Role;
import icu.telepathystudios.puretender.repo.bid.BidDocumentRepo;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class BlockchainServicesTest {

    private final DocumentHashService documentHashService = new DocumentHashService();

    @Mock FabricService fabricService;
    @Mock BidDocumentRepo bidDocumentRepo;

    private BlockchainRecordService recordService;

    @BeforeEach
    void setUp() {
        recordService = new BlockchainRecordService(fabricService, documentHashService, bidDocumentRepo);
    }

    @Test
    void sha256ReturnsStandardHexDigest() {
        assertEquals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                documentHashService.sha256("abc".getBytes(StandardCharsets.UTF_8)));
    }

    @Test
    void matchesAcceptsCorrectHash() {
        byte[] content = "proposal".getBytes(StandardCharsets.UTF_8);

        assertTrue(documentHashService.matches(content, documentHashService.sha256(content)));
    }

    @Test
    void matchesTrimsAndIgnoresHashLetterCase() {
        byte[] content = "proposal".getBytes(StandardCharsets.UTF_8);
        String uppercaseHash = documentHashService.sha256(content).toUpperCase();

        assertTrue(documentHashService.matches(content, "  " + uppercaseHash + "  "));
    }

    @Test
    void matchesRejectsNullAndIncorrectHashes() {
        byte[] content = "proposal".getBytes(StandardCharsets.UTF_8);

        assertFalse(documentHashService.matches(null, "abc"));
        assertFalse(documentHashService.matches(content, null));
        assertFalse(documentHashService.matches(content, "incorrect"));
    }

    @Test
    void createTenderRecordSubmitsExpectedTenderIdentifier() throws Exception {
        Tender tender = tender();

        recordService.createTenderRecord(tender);

        verify(fabricService).createIntegrityRecord(eq("TENDER:" + tender.getId()), eq("TENDER"), eq(""), anyString());
    }

    @Test
    void updateTenderRecordSubmitsUpdatedHash() throws Exception {
        Tender tender = tender();

        recordService.updateTenderRecord(tender);

        verify(fabricService).updateIntegrityRecord(eq("TENDER:" + tender.getId()), anyString());
    }

    @Test
    void hashTenderIsDeterministicForSameTenderData() {
        Tender tender = tender();

        assertEquals(recordService.hashTender(tender), recordService.hashTender(tender));
    }

    @Test
    void ledgerReadMethodsDelegateToFabricService() throws Exception {
        when(fabricService.integrityRecordExists("TENDER:one")).thenReturn(true);
        when(fabricService.readIntegrityRecord("TENDER:one")).thenReturn("{\"payloadHash\":\"abc\"}");

        assertTrue(recordService.integrityRecordExists("TENDER:one"));
        assertEquals("{\"payloadHash\":\"abc\"}", recordService.readIntegrityRecord("TENDER:one"));
    }

    @Test
    void createBidRecordLoadsVerifiedStoredDocumentAndSubmitsIt() throws Exception {
        User contractor = new User();
        contractor.setId(UUID.randomUUID());
        contractor.setFullName("Contractor");
        contractor.setRole(Role.CONTRACTOR);
        Tender tender = tender();
        Bid bid = new Bid();
        bid.setId(UUID.randomUUID());
        bid.setTender(tender);
        bid.setContractor(contractor);
        bid.setQuotedAmount(new BigDecimal("125.00"));
        bid.setSubmittedAt(Instant.parse("2026-01-01T00:00:00Z"));
        BidDocument document = new BidDocument();
        document.setBid(bid);
        document.setFileData("proposal".getBytes(StandardCharsets.UTF_8));
        document.setSha256Hash(documentHashService.sha256(document.getFileData()));
        when(bidDocumentRepo.findByBid_Id(bid.getId())).thenReturn(Optional.of(document));

        recordService.createBidRecord(bid);

        verify(fabricService).createIntegrityRecord(eq("BID:" + bid.getId()), eq("BID"),
                eq("TENDER:" + tender.getId()), anyString());
    }

    @Test
    void updateBidRecordRejectsDocumentWithInvalidHash() {
        Bid bid = new Bid();
        BidDocument document = new BidDocument();
        document.setFileData("proposal".getBytes(StandardCharsets.UTF_8));
        document.setSha256Hash("bad-hash");

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> recordService.updateBidRecord(bid, document));

        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode().value());
        verifyNoInteractions(fabricService);
    }

    private static Tender tender() {
        User authority = new User();
        authority.setId(UUID.randomUUID());
        Tender tender = new Tender();
        tender.setId(UUID.randomUUID());
        tender.setTitle("Road Works");
        tender.setDescription("Repair roads");
        tender.setEstimatedValue(new BigDecimal("1000.00"));
        tender.setSubmissionDeadline(Instant.parse("2026-02-01T00:00:00Z"));
        tender.setOpeningDate(Instant.parse("2026-02-02T00:00:00Z"));
        tender.setAuthority(authority);
        return tender;
    }
}
