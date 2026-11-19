package icu.telepathystudios.puretender.service.auth;

import icu.telepathystudios.puretender.dto.auth.AccountStatusResponse;
import icu.telepathystudios.puretender.dto.auth.AuthResponse;
import icu.telepathystudios.puretender.dto.auth.LoginRequest;
import icu.telepathystudios.puretender.dto.auth.RegisterRequest;
import icu.telepathystudios.puretender.model.classes.User;
import icu.telepathystudios.puretender.model.enums.AccountStatus;
import icu.telepathystudios.puretender.model.enums.Role;
import icu.telepathystudios.puretender.repo.AuthRepo;
import icu.telepathystudios.puretender.util.JwtUtil;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.server.ResponseStatusException;

import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    @Mock AuthRepo authRepo;
    @Mock PasswordEncoder passwordEncoder;
    @Mock JwtUtil jwtUtil;
    @InjectMocks AuthService service;

    @Test
    void registerNormalizesEmailAndTrimsName() {
        when(authRepo.existsByEmail("person@example.com")).thenReturn(false);
        when(passwordEncoder.encode("password123")).thenReturn("encoded");
        when(authRepo.saveAndFlush(any(User.class))).thenAnswer(invocation -> {
            User user = invocation.getArgument(0);
            user.setId(UUID.randomUUID());
            return user;
        });
        when(jwtUtil.generateToken("person@example.com", Role.CONTRACTOR.name())).thenReturn("token");

        AuthResponse response = service.register(
                new RegisterRequest("  Person Name  ", " PERSON@Example.com ", "password123"),
                Role.CONTRACTOR);

        assertEquals("person@example.com", response.email());
        assertEquals("Person Name", response.fullName());
        assertEquals(Role.CONTRACTOR, response.role());
        assertEquals("token", response.accessToken());
        verify(passwordEncoder).encode("password123");
    }

    @Test
    void registerRejectsDuplicateEmail() {
        when(authRepo.existsByEmail("person@example.com")).thenReturn(true);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.register(new RegisterRequest("Person", " PERSON@example.com ", "password123"), Role.CONTRACTOR));

        assertEquals(HttpStatus.CONFLICT.value(), exception.getStatusCode().value());
        verify(authRepo, never()).saveAndFlush(any());
    }

    @Test
    void registerDoesNotAllowAdminRole() {
        when(authRepo.existsByEmail("admin@example.com")).thenReturn(false);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.register(new RegisterRequest("Admin", "admin@example.com", "password123"), Role.ADMIN));

        assertEquals(HttpStatus.FORBIDDEN.value(), exception.getStatusCode().value());
        verify(authRepo, never()).saveAndFlush(any());
    }

    @Test
    void loginReturnsTokenForValidCredentials() {
        User user = user("person@example.com", Role.CONTRACTOR, AccountStatus.PENDING);
        when(authRepo.findByEmail("person@example.com")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("password123", "encoded")).thenReturn(true);
        when(jwtUtil.generateToken("person@example.com", Role.CONTRACTOR.name())).thenReturn("token");
        user.setPasswordHash("encoded");

        AuthResponse response = service.login(new LoginRequest(" PERSON@example.com ", "password123"));

        assertEquals("token", response.accessToken());
        assertEquals(AccountStatus.PENDING, response.accountStatus());
        verify(jwtUtil).generateToken("person@example.com", Role.CONTRACTOR.name());
    }

    @Test
    void loginRejectsUnknownEmail() {
        when(authRepo.findByEmail("missing@example.com")).thenReturn(Optional.empty());

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.login(new LoginRequest("missing@example.com", "password123")));

        assertEquals(HttpStatus.UNAUTHORIZED.value(), exception.getStatusCode().value());
    }

    @Test
    void loginRejectsIncorrectPassword() {
        User user = user("person@example.com", Role.CONTRACTOR, AccountStatus.VERIFIED);
        user.setPasswordHash("encoded");
        when(authRepo.findByEmail("person@example.com")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("wrongpass", "encoded")).thenReturn(false);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.login(new LoginRequest("person@example.com", "wrongpass")));

        assertEquals(HttpStatus.UNAUTHORIZED.value(), exception.getStatusCode().value());
    }

    @Test
    void loginRejectsRejectedAccount() {
        User user = user("person@example.com", Role.CONTRACTOR, AccountStatus.REJECTED);
        user.setPasswordHash("encoded");
        when(authRepo.findByEmail("person@example.com")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("password123", "encoded")).thenReturn(true);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.login(new LoginRequest("person@example.com", "password123")));

        assertEquals(HttpStatus.FORBIDDEN.value(), exception.getStatusCode().value());
    }

    @Test
    void loginRejectsDisabledAccount() {
        User user = user("person@example.com", Role.CONTRACTOR, AccountStatus.DISABLED);
        user.setPasswordHash("encoded");
        when(authRepo.findByEmail("person@example.com")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("password123", "encoded")).thenReturn(true);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.login(new LoginRequest("person@example.com", "password123")));

        assertEquals(HttpStatus.FORBIDDEN.value(), exception.getStatusCode().value());
    }

    @Test
    void getCurrentAccountStatusReturnsStatusForNormalizedEmail() {
        when(authRepo.findByEmail("person@example.com"))
                .thenReturn(Optional.of(user("person@example.com", Role.CONTRACTOR, AccountStatus.VERIFIED)));

        AccountStatusResponse response = service.getCurrentAccountStatus(" PERSON@example.com ");

        assertEquals(AccountStatus.VERIFIED, response.accountStatus());
    }

    @Test
    void getCurrentAccountStatusReturnsNotFoundForUnknownUser() {
        when(authRepo.findByEmail("missing@example.com")).thenReturn(Optional.empty());

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.getCurrentAccountStatus("missing@example.com"));

        assertEquals(HttpStatus.NOT_FOUND.value(), exception.getStatusCode().value());
    }

    private static User user(String email, Role role, AccountStatus status) {
        User user = new User();
        user.setId(UUID.randomUUID());
        user.setFullName("Person Name");
        user.setEmail(email);
        user.setRole(role);
        user.setStatus(status);
        return user;
    }
}
