# Simple File Upload Server Project

## Project Overview
The Simple File Upload Server is a Flask-based application designed for secure, temporary file sharing and mobile app log uploads. It follows a clean MVC architecture and implements modern web standards for both API and user interface interactions.

## Project Rules and Guidelines

### Code Organization
1. **MVC Pattern**
   - Models: Place all data models in `src/models/`
   - Views: Store templates in `src/templates/`
   - Controllers: Keep business logic in `src/controllers/`

2. **File Structure**
   - Source code belongs in `src/`
   - Configuration files in root directory
   - Temporary files in `tmp/uploads/`
   - Templates in `src/templates/`

### Development Rules
1. **Code Style**
   - Follow PEP 8 guidelines for Python code
   - Use type hints where possible
   - Document all public functions and classes
   - Keep functions focused and single-purpose

2. **Security Requirements**
   - All uploads must be authenticated with API key
   - File names must be sanitized
   - SSL required for production
   - Implement proper error handling
   - Clean up expired/abandoned files

3. **API Guidelines**
   - Maintain backward compatibility
   - Document all endpoint changes
   - Include proper error responses
   - Use consistent response formats
   - Validate all input parameters

4. **Feature Implementation**
   - Add tests for new features
   - Update documentation
   - Follow chunked upload protocol for large files
   - Maintain mobile app compatibility
   - Consider both WiFi and mobile network scenarios

### Testing Requirements
1. **New Features**
   - Unit tests required
   - Test both success and failure cases
   - Include mobile network testing
   - Verify chunked upload functionality

2. **Performance Testing**
   - Test with files >100MB
   - Verify timeout configurations
   - Test under various network conditions
   - Monitor memory usage

### Deployment Rules
1. **Docker Requirements**
   - Use multi-stage builds
   - Include only necessary files
   - Set proper permissions
   - Configure appropriate timeouts

2. **Production Setup**
   - SSL certificates required
   - Strong CLIENT_KEY required
   - Proper file cleanup configuration
   - Monitoring setup

## Documentation Structure

### Core Documentation
1. **README.md**
   - Basic setup and configuration
   - API endpoint documentation
   - Docker deployment instructions
   - Security best practices
   [View README.md for details](README.md)

2. **TASK.md**
   - Project roadmap
   - Feature implementation status
   - Future enhancements
   - Current objectives
   [View TASK.md for progress](TASK.md)

3. **LARGE_UPLOAD.md**
   - Chunked upload implementation
   - Network handling strategies
   - Mobile optimization
   - Technical specifications
   [View LARGE_UPLOAD.md for implementation details](LARGE_UPLOAD.md)

## Version Control Rules
1. **Branching Strategy**
   - Main branch: production-ready code
   - Develop branch: integration branch
   - Feature branches: feature/* prefix
   - Hotfix branches: hotfix/* prefix

2. **Commit Guidelines**
   - Clear, descriptive commit messages
   - Reference issue numbers
   - Single responsibility per commit
   - Include relevant tests

3. **Release Process**
   - Tag all releases (v*.*.*)
   - Update version.txt
   - Generate change logs
   - Test deployment process

## CI/CD Pipeline
1. **Automated Processes**
   - Build testing
   - Unit test execution
   - Docker image building
   - Version tagging
   - DockerHub publishing

2. **Quality Gates**
   - All tests must pass
   - Code coverage requirements
   - No security vulnerabilities
   - Proper version tagging

## Monitoring and Maintenance
1. **Server Health**
   - Regular cleanup of expired files
   - Monitor disk usage
   - Track API usage
   - Log error rates

2. **Performance Metrics**
   - Upload success rates
   - Download completion rates
   - Response times
   - Chunked upload efficiency

## Support and Updates
1. **Issue Management**
   - Use GitHub issues for tracking
   - Label issues appropriately
   - Follow security disclosure process
   - Maintain changelog

2. **Documentation Updates**
   - Keep API docs current
   - Update setup instructions
   - Document known issues
   - Maintain upgrade guides