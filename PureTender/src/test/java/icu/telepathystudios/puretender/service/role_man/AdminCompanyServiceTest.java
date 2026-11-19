package icu.telepathystudios.puretender.service.role_man;

import icu.telepathystudios.puretender.dto.company.CompanyProfileRequest;
import icu.telepathystudios.puretender.model.classes.CompanyProfile;
import icu.telepathystudios.puretender.model.classes.Tender;
import icu.telepathystudios.puretender.model.classes.User;
import icu.telepathystudios.puretender.model.enums.AccountStatus;
import icu.telepathystudios.puretender.model.enums.Role;
import icu.telepathystudios.puretender.model.enums.TenderStatus;
import icu.telepathystudios.puretender.repo.AuthRepo;
import icu.telepathystudios.puretender.repo.CompanyProfileRepo;
import icu.telepathystudios.puretender.repo.admin.AdminRepo;
import icu.telepathystudios.puretender.repo.admin.TenderEvaluatorRepo;
import icu.telepathystudios.puretender.repo.tender.TenderRepo;
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
class AdminCompanyServiceTest {

    @Mock AdminRepo adminRepo;
    @Mock CompanyProfileRepo companyProfileRepo;
    @Mock TenderEvaluatorRepo tenderEvaluatorRepo;
    @Mock TenderRepo tenderRepo;
    @Mock AuthRepo authRepo;

    private AdminService adminService;
    private CompanyProfileService profileService;

    @BeforeEach
    void setUp() {
        adminService = new AdminService(adminRepo, companyProfileRepo, tenderEvaluatorRepo, tenderRepo, authRepo);
        profileService = new CompanyProfileService(companyProfileRepo, authRepo);
    }

    @Test
    void verifyUserChangesPendingAccountToVerified() {
        User user = user(Role.CONTRACTOR, AccountStatus.PENDING);
        when(adminRepo.findById(user.getId())).thenReturn(Optional.of(user));
        when(adminRepo.save(user)).thenReturn(user);

        var response = adminService.verifyUser(user.getId());

        assertEquals(AccountStatus.VERIFIED, response.status());
        verify(adminRepo).save(user);
    }

    @Test
    void verifyUserRejectsAccountThatIsNotPending() {
        User user = user(Role.CONTRACTOR, AccountStatus.VERIFIED);
        when(adminRepo.findById(user.getId())).thenReturn(Optional.of(user));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> adminService.verifyUser(user.getId()));

        assertEquals(HttpStatus.CONFLICT.value(), exception.getStatusCode().value());
    }

    @Test
    void disableUserRejectsAdminAccount() {
        User user = user(Role.ADMIN, AccountStatus.VERIFIED);
        when(adminRepo.findById(user.getId())).thenReturn(Optional.of(user));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> adminService.disableUser(user.getId()));

        assertEquals(HttpStatus.FORBIDDEN.value(), exception.getStatusCode().value());
    }

    @Test
    void enableUserRestoresDisabledAccount() {
        User user = user(Role.CONTRACTOR, AccountStatus.DISABLED);
        when(adminRepo.findById(user.getId())).thenReturn(Optional.of(user));
        when(adminRepo.save(user)).thenReturn(user);

        var response = adminService.enableUser(user.getId());

        assertEquals(AccountStatus.VERIFIED, response.status());
    }

    @Test
    void approveTenderPublishesTenderAndAssignsEvaluator() {
        User admin = user(Role.ADMIN, AccountStatus.VERIFIED);
        User evaluator = user(Role.EVALUATOR, AccountStatus.VERIFIED);
        User authority = user(Role.AUTHORITY, AccountStatus.VERIFIED);
        Tender tender = tender(authority, TenderStatus.SUBMITTED);
        Authentication authentication = mock(Authentication.class);
        when(authentication.getName()).thenReturn("admin@example.com");
        when(authRepo.findByEmail("admin@example.com")).thenReturn(Optional.of(admin));
        when(authRepo.findById(admin.getId())).thenReturn(Optional.of(admin));
        when(authRepo.findById(evaluator.getId())).thenReturn(Optional.of(evaluator));
        when(tenderRepo.findById(tender.getId())).thenReturn(Optional.of(tender));
        when(tenderRepo.save(tender)).thenReturn(tender);

        var response = adminService.approveTender(tender.getId(), evaluator.getId(), authentication);

        assertEquals(TenderStatus.PUBLISHED, response.status());
        assertNotNull(tender.getPublishedAt());
        verify(tenderEvaluatorRepo).save(any());
    }

    @Test
    void rejectTenderChangesSubmittedTenderToRejected() {
        User authority = user(Role.AUTHORITY, AccountStatus.VERIFIED);
        Tender tender = tender(authority, TenderStatus.SUBMITTED);
        when(tenderRepo.findById(tender.getId())).thenReturn(Optional.of(tender));
        when(tenderRepo.save(tender)).thenReturn(tender);

        var response = adminService.rejectTender(tender.getId(), "Incomplete documents");

        assertEquals(TenderStatus.REJECTED, response.status());
        assertEquals("Incomplete documents", response.rejectionReason());
    }

    @Test
    void createProfileSavesProfileForAuthorizedCompanyUser() {
        User user = user(Role.CONTRACTOR, AccountStatus.PENDING);
        Authentication authentication = mock(Authentication.class);
        when(authentication.getName()).thenReturn(user.getEmail());
        when(authRepo.findByEmail(user.getEmail())).thenReturn(Optional.of(user));
        when(authRepo.findById(user.getId())).thenReturn(Optional.of(user));
        when(companyProfileRepo.existsByUserId(user.getId())).thenReturn(false);
        when(companyProfileRepo.save(any(CompanyProfile.class))).thenAnswer(invocation -> {
            CompanyProfile profile = invocation.getArgument(0);
            profile.setId(UUID.randomUUID());
            return profile;
        });

        var response = profileService.createProfile(authentication, profileRequest());

        assertEquals(user.getId(), response.userId());
        assertEquals("Example Ltd", response.companyName());
    }

    @Test
    void createProfileRejectsExistingProfile() {
        User user = user(Role.CONTRACTOR, AccountStatus.PENDING);
        Authentication authentication = mock(Authentication.class);
        when(authentication.getName()).thenReturn(user.getEmail());
        when(authRepo.findByEmail(user.getEmail())).thenReturn(Optional.of(user));
        when(authRepo.findById(user.getId())).thenReturn(Optional.of(user));
        when(companyProfileRepo.existsByUserId(user.getId())).thenReturn(true);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> profileService.createProfile(authentication, profileRequest()));

        assertEquals(HttpStatus.CONFLICT.value(), exception.getStatusCode().value());
    }

    @Test
    void updateProfileForbidsChangingVerifiedAccountDetails() {
        User user = user(Role.CONTRACTOR, AccountStatus.VERIFIED);
        Authentication authentication = mock(Authentication.class);
        when(authentication.getName()).thenReturn(user.getEmail());
        when(authRepo.findByEmail(user.getEmail())).thenReturn(Optional.of(user));
        when(authRepo.findById(user.getId())).thenReturn(Optional.of(user));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> profileService.updateProfile(authentication, profileRequest()));

        assertEquals(HttpStatus.FORBIDDEN.value(), exception.getStatusCode().value());
    }

    private static CompanyProfileRequest profileRequest() {
        return new CompanyProfileRequest("Example Ltd", "REG-101", "22AAAAA0000A1Z5",
                "ABCDE1234F", "1 Main Street", "+91 9876543210", "https://example.com");
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

    private static Tender tender(User authority, TenderStatus status) {
        Tender tender = new Tender();
        tender.setId(UUID.randomUUID());
        tender.setAuthority(authority);
        tender.setTitle("Road Works");
        tender.setDescription("Repair roads");
        tender.setEstimatedValue(new BigDecimal("1000.00"));
        tender.setSubmissionDeadline(Instant.now().plusSeconds(3600));
        tender.setOpeningDate(Instant.now().plusSeconds(7200));
        tender.setStatus(status);
        return tender;
    }
}
