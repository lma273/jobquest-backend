package com.krish.jobquestbackend;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/candidates")
// Có thể bỏ @CrossOrigin ở đây nếu bạn đã cấu hình CORS global trong SecurityConfig
@CrossOrigin(origins = "*")
public class CandidateController {

    @Autowired
    private CandidateService candidateService;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @GetMapping
    public ResponseEntity<List<Candidate>> getAllCandidates() {
        return new ResponseEntity<>(candidateService.allCandidates(), HttpStatus.OK);
    }

    //    TO BE REMOVED LATER, USING JUST FOR TESTING PURPOSES
    @GetMapping("/{email}")
    public ResponseEntity<Optional<Candidate>> getSingleCandidate(@PathVariable String email) {
        return new ResponseEntity<>(candidateService.singleCandidate(email), HttpStatus.OK);
    }

    @PostMapping("/signup")
    public ResponseEntity<?> signup(@RequestBody Candidate candidate) {
        Optional<Candidate> existingCandidate = candidateService.singleCandidate(candidate.getEmail());
        if (existingCandidate.isPresent()) {
            return new ResponseEntity<>("Email already taken", HttpStatus.BAD_REQUEST);
        }

        Candidate created = candidateService.createCandidate(candidate);

        // ⭐ Tạo JWT ngay sau khi tạo tài khoản
        String token = jwtTokenProvider.createToken(created.getEmail(), "CANDIDATE");

        Map<String, Object> body = new HashMap<>();
        body.put("token", token);
        body.put("candidate", created);

        return new ResponseEntity<>(body, HttpStatus.CREATED);
    }


    // ⭐ Stateless login: xác thực + trả JWT nội bộ (HS256)
    @PostMapping("/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody Map<String, String> payload) {
        String email = payload.get("email");
        String password = payload.get("password");

        Optional<Candidate> candidateOpt = candidateService.singleCandidate(email);
        if (candidateOpt.isEmpty()) {
            return new ResponseEntity<>(Map.of("error", "Email not found"), HttpStatus.NOT_FOUND);
        }

        Candidate candidate = candidateOpt.get();
        if (!passwordEncoder.matches(password, candidate.getPassword())) {
            return new ResponseEntity<>(Map.of("error", "Wrong password"), HttpStatus.UNAUTHORIZED);
        }

        String token = jwtTokenProvider.createToken(candidate.getEmail(), "CANDIDATE");

        Map<String, Object> body = new HashMap<>();
        body.put("token", token);
        body.put("candidate", candidate);

        return new ResponseEntity<>(body, HttpStatus.OK);
    }

    // ⭐ Stateless logout: FE tự xóa token, BE trả OK cho đẹp flow
    @PostMapping("/logout")
    public ResponseEntity<String> logout() {
        return new ResponseEntity<>("Logged out", HttpStatus.OK);
    }
}
