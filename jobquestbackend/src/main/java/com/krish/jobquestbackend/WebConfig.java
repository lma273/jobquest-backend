// package com.krish.jobquestbackend;

// import org.springframework.context.annotation.Bean;
// import org.springframework.context.annotation.Configuration;
// import org.springframework.web.servlet.config.annotation.CorsRegistry;
// import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

// @Configuration
// public class WebConfig {
    
//     @Bean
//     public WebMvcConfigurer corsConfigurer() {
//         return new WebMvcConfigurer() {
//             @Override
//             public void addCorsMappings(CorsRegistry registry) {
//                 registry.addMapping("/**")
//                         .allowedOrigins("*") // ⭐ TẠM THỜI cho phép TẤT CẢ
//                         .allowedMethods("*")
//                         .allowedHeaders("*");
//             }
//         };
//     }
// }
// // package com.krish.jobquestbackend;
// // import org.springframework.context.annotation.Bean;
// // import org.springframework.context.annotation.Configuration;
// // import org.springframework.web.servlet.config.annotation.CorsRegistry;
// // import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
// // @Configuration
// // public class WebConfig {

// //     @Bean
// //     public WebMvcConfigurer corsConfigurer() {
// //         return new WebMvcConfigurer() {
// //             @Override
// //             public void addCorsMappings(CorsRegistry registry) {
// //                 registry.addMapping("/**") // Áp dụng cho tất cả endpoint
// //                         .allowedOrigins("http://localhost:5173") // Cho phép frontend gọi API
// //                         .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
// //                         .allowedHeaders("*")
// //                         .allowCredentials(true);
// //             }
// //         };
// //     }
// // }