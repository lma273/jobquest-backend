package com.krish.jobquestbackend;

import org.bson.types.ObjectId;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/recruiters")
// Có thể bỏ @CrossOrigin ở đây nếu đã cấu hình CORS global
public class RecruiterController {

    @Autowired
    private RecruiterService recruiterService;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @GetMapping
    public ResponseEntity<List<Recruiter>> getAllRecruiters() {
        return new ResponseEntity<>(recruiterService.allRecruiters(), HttpStatus.OK);
    }

    // ⭐ Thêm endpoint test
    @GetMapping("/test")
    public String test() {
        return "Working!";
    }

    //    TO BE REMOVED LATER, USING JUST FOR TESTING PURPOSES
    @GetMapping("/{email}")
    public ResponseEntity<Optional<Recruiter>> getSingleRecruiter(@PathVariable String email) {
        return new ResponseEntity<>(recruiterService.singleRecruiter(email), HttpStatus.OK);
    }

    @PostMapping("/{email}/appendjob")
    public ResponseEntity<?> appendJob(@PathVariable String email, @RequestBody Map<String, String> body) {
        try {
            String jobId = body.get("jobId");
            Recruiter updatedRecruiter = recruiterService.addJobToRecruiter(email, jobId);
            return new ResponseEntity<>(updatedRecruiter, HttpStatus.OK);
        } catch (Exception e) {
            e.printStackTrace();
            return new ResponseEntity<>("Something went wrong", HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @PostMapping("/{email}/removejob")
    public ResponseEntity<Recruiter> removeJob(@PathVariable String email, @RequestBody String jobId) {
        return new ResponseEntity<>(recruiterService.removeJobFromRecruiter(email, jobId), HttpStatus.OK);
    }

    @PostMapping("/signup")
    public ResponseEntity<?> signup(@RequestBody Recruiter recruiter) {
        Optional<Recruiter> existingRecruiter = recruiterService.singleRecruiter(recruiter.getEmail());
        if (existingRecruiter.isPresent()) {
            return new ResponseEntity<>("Email already taken", HttpStatus.BAD_REQUEST);
        }

        Recruiter created = recruiterService.createRecruiter(recruiter);

        // ⭐ Tạo JWT ngay sau khi tạo tài khoản
        String token = jwtTokenProvider.createToken(created.getEmail(), "RECRUITER");

        Map<String, Object> body = new HashMap<>();
        body.put("token", token);
        body.put("recruiter", created);

        // 201 Created kèm token để FE lưu thẳng và coi như đã login
        return new ResponseEntity<>(body, HttpStatus.CREATED);
    }

    // ⭐ Stateless login: xác thực + trả JWT nội bộ (HS256)
    @PostMapping("/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody Map<String, String> payload) {
        String email = payload.get("email");
        String password = payload.get("password");

        Optional<Recruiter> recruiterOpt = recruiterService.singleRecruiter(email);
        if (recruiterOpt.isEmpty()) {
            return new ResponseEntity<>(Map.of("error", "Email not found"), HttpStatus.NOT_FOUND);
        }

        Recruiter recruiter = recruiterOpt.get();
        if (!passwordEncoder.matches(password, recruiter.getPassword())) {
            return new ResponseEntity<>(Map.of("error", "Wrong password"), HttpStatus.UNAUTHORIZED);
        }

        String token = jwtTokenProvider.createToken(recruiter.getEmail(), "RECRUITER");

        Map<String, Object> body = new HashMap<>();
        body.put("token", token);
        body.put("recruiter", recruiter);

        return new ResponseEntity<>(body, HttpStatus.OK);
    }

    // ⭐ Stateless logout: FE tự xóa token, BE trả OK
    @PostMapping("/logout")
    public ResponseEntity<String> logout() {
        return new ResponseEntity<>("Logged out", HttpStatus.OK);
    }
}
