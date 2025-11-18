package com.krish.jobquestbackend;

import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.Optional;

@Slf4j
@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private final JwtDecoder idTokenDecoder;
    private final CandidateService candidateService;
    private final RecruiterService recruiterService;
    private final JwtTokenProvider jwtTokenProvider;

    // --- SSO LOGIN (public) ---
    @PostMapping("/sso-login")
    public ResponseEntity<?> ssoLogin(@RequestBody IdTokenReq req) {
        try {
            if (req == null || req.getId_token() == null || req.getId_token().isBlank()) {
                return ResponseEntity.badRequest().body(Map.of(
                        "code", "MISSING_ID_TOKEN",
                        "message", "Missing id_token"
                ));
            }

            Jwt idToken = idTokenDecoder.decode(req.getId_token());
            String sub = idToken.getSubject();                 // auth0|xxxx
            String email = idToken.getClaimAsString("email");  // email từ Google/IdP

            // --- 1) Ưu tiên: tìm theo sub đã link ---
            Optional<Candidate> candBySub = candidateService.findByAuth0Sub(sub);
            if (candBySub.isPresent()) {
                Candidate u = candBySub.get();
                candidateService.updateLastLoginProvider(u, "auth0");
                String token = jwtTokenProvider.createToken(u.getEmail(), "CANDIDATE");
                return ResponseEntity.ok(new LoginRes(token, "candidate", u));
            }
            Optional<Recruiter> recBySub = recruiterService.findByAuth0Sub(sub);
            if (recBySub.isPresent()) {
                Recruiter u = recBySub.get();
                recruiterService.updateLastLoginProvider(u, "auth0");
                String token = jwtTokenProvider.createToken(u.getEmail(), "RECRUITER");
                return ResponseEntity.ok(new LoginRes(token, "recruiter", u));
            }

            // --- 2) Chưa link: auto-link theo email NẾU user đã tồn tại ---
            if (email != null && !email.isBlank()) {
                Optional<Candidate> candByEmail = candidateService.findByEmail(email);
                if (candByEmail.isPresent()) {
                    Candidate u = candidateService.linkAuth0(candByEmail.get(), sub, true);
                    candidateService.updateLastLoginProvider(u, "auth0");
                    String token = jwtTokenProvider.createToken(u.getEmail(), "CANDIDATE");
                    return ResponseEntity.ok(new LoginRes(token, "candidate", u));
                }
                Optional<Recruiter> recByEmail = recruiterService.findByEmail(email);
                if (recByEmail.isPresent()) {
                    Recruiter u = recruiterService.linkAuth0(recByEmail.get(), sub, true);
                    recruiterService.updateLastLoginProvider(u, "auth0");
                    String token = jwtTokenProvider.createToken(u.getEmail(), "RECRUITER");
                    return ResponseEntity.ok(new LoginRes(token, "recruiter", u));
                }
            }

            // --- 3) Không tìm thấy ai ⇒ KHÔNG tạo mới, trả 404 để frontend điều hướng đăng ký ---
            return ResponseEntity.status(404).body(Map.of(
                    "code", "USER_NOT_FOUND",
                    "message", "Tài khoản chưa tồn tại. Vui lòng đăng ký.",
                    "emailHint", email // để UI prefill
            ));

        } catch (JwtException e) {
            log.warn("Invalid ID token: {}", e.getMessage()); // <-- xem message cụ thể
            // soi nhanh header/payload để đối chiếu iss/aud/alg/kid
            try {
                String[] p = req.getId_token().split("\\.");
                String header = new String(java.util.Base64.getUrlDecoder().decode(p[0]));
                String payload = new String(java.util.Base64.getUrlDecoder().decode(p[1]));
                log.warn("IDT header={}, payload={}", header, payload);
            } catch (Exception ignore) {}
            return ResponseEntity.status(401).body("Invalid id_token");
        } catch (Exception e) {
            log.error("SSO login failed", e);
            return ResponseEntity.status(500).body(Map.of(
                    "code", "INTERNAL_ERROR",
                    "message", "Internal error"
            ));
        }
    }


    // --- LINK SSO (cần JWT nội bộ, user đã login local) ---
    @PostMapping("/sso-link")
    public ResponseEntity<?> ssoLink(
            @RequestHeader(value = "Authorization", required = false) String authz,
            @RequestBody LinkReq req
    ) {
        try {
            if (authz == null || !authz.startsWith("Bearer ")) {
                return ResponseEntity.status(401).body("Missing Authorization Bearer token");
            }
            if (req == null || req.getId_token() == null || req.getId_token().isBlank()) {
                return ResponseEntity.badRequest().body("Missing id_token");
            }

            String bearer = authz.substring(7);
            String email = jwtTokenProvider.getUsername(bearer);

            Jwt idToken = idTokenDecoder.decode(req.getId_token());
            String sub = idToken.getSubject();

            Optional<Candidate> cand = candidateService.findByEmail(email);
            if (cand.isPresent()) {
                candidateService.linkAuth0(cand.get(), sub, Boolean.TRUE.equals(req.getRemember()));
                return ResponseEntity.ok().build();
            }
            Optional<Recruiter> rec = recruiterService.findByEmail(email);
            if (rec.isPresent()) {
                recruiterService.linkAuth0(rec.get(), sub, Boolean.TRUE.equals(req.getRemember()));
                return ResponseEntity.ok().build();
            }
            return ResponseEntity.badRequest().body("User not found for email: " + email);

        } catch (JwtException e) {
            log.warn("Invalid ID token on link: {}", e.getMessage());
            return ResponseEntity.status(401).body("Invalid id_token");
        } catch (Exception e) {
            log.error("SSO link failed", e);
            return ResponseEntity.status(500).body("Internal error");
        }
    }

    // --- UNLINK SSO ---
    @PostMapping("/sso-unlink")
    public ResponseEntity<?> ssoUnlink(
            @RequestHeader(value = "Authorization", required = false) String authz
    ) {
        try {
            if (authz == null || !authz.startsWith("Bearer ")) {
                return ResponseEntity.status(401).body("Missing Authorization Bearer token");
            }
            String bearer = authz.substring(7);
            String email = jwtTokenProvider.getUsername(bearer);

            Optional<Candidate> cand = candidateService.findByEmail(email);
            if (cand.isPresent()) {
                candidateService.unlinkAuth0(cand.get());
                return ResponseEntity.ok().build();
            }
            Optional<Recruiter> rec = recruiterService.findByEmail(email);
            if (rec.isPresent()) {
                recruiterService.unlinkAuth0(rec.get());
                return ResponseEntity.ok().build();
            }
            return ResponseEntity.badRequest().body("User not found for email: " + email);

        } catch (Exception e) {
            log.error("SSO unlink failed", e);
            return ResponseEntity.status(500).body("Internal error");
        }
    }

    // ==== DTOs ====
    @Data
    public static class IdTokenReq { private String id_token; }

    @Data
    public static class LinkReq {
        private String id_token;
        private Boolean remember;
    }

    @Data
    public static class LoginRes {
        private final String token;
        private final String role;   // "candidate" | "recruiter"
        private final Object profile;
    }
}
