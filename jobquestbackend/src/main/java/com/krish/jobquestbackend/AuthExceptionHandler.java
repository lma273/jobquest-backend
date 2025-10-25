package com.krish.jobquestbackend;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.security.oauth2.jwt.JwtValidationException;
import io.jsonwebtoken.JwtException;

@RestControllerAdvice
public class AuthExceptionHandler {

    @ExceptionHandler({ JwtValidationException.class, JwtException.class, IllegalArgumentException.class })
    public ResponseEntity<?> handleJwt(Exception ex) {
        return ResponseEntity.status(401).body("Invalid or expired token");
    }
}