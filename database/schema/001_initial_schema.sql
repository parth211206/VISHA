-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enums
CREATE TYPE user_role AS ENUM ('clinician', 'admin', 'researcher');
CREATE TYPE case_status AS ENUM ('open', 'analyzing', 'pending_review', 'confirmed', 'closed');
CREATE TYPE venom_category AS ENUM ('neurotoxic', 'cytotoxic', 'hemotoxic', 'mixed', 'unknown');
CREATE TYPE medical_relevance AS ENUM ('high', 'medium', 'low', 'unknown');
CREATE TYPE prediction_source AS ENUM ('ml_binary', 'ml_species', 'clinical_rules', 'geographic_prior', 'clinician');
CREATE TYPE audit_action AS ENUM (
    'case_created', 'case_updated', 'case_confirmed', 'case_closed',
    'prediction_generated', 'clinician_review_added', 'antivenom_looked_up',
    'surveillance_record_created', 'user_login', 'user_logout',
    'admin_action'
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role user_role NOT NULL DEFAULT 'clinician',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Cases
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_number VARCHAR(50) UNIQUE NOT NULL,
    status case_status NOT NULL DEFAULT 'open',
    created_by UUID NOT NULL REFERENCES users(id),
    assigned_to UUID REFERENCES users(id),
    
    patient_age_years INTEGER,
    patient_sex VARCHAR(20),
    
    bite_date TIMESTAMPTZ,
    bite_time_approx BOOLEAN DEFAULT false,
    bite_site VARCHAR(100),
    
    incident_state VARCHAR(100),
    incident_district VARCHAR(100),
    incident_location_description TEXT,
    incident_coordinates GEOMETRY(Point, 4326),
    
    snake_observed BOOLEAN,
    snake_description TEXT,
    snake_image_path VARCHAR(500),
    
    symptoms JSONB NOT NULL DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ
);

-- Predictions
CREATE TABLE case_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    source prediction_source NOT NULL,
    
    binary_label VARCHAR(50),
    binary_confidence FLOAT,
    venomous_probability FLOAT,
    
    species_available BOOLEAN NOT NULL DEFAULT false,
    species_label VARCHAR(200),
    genus_label VARCHAR(200),
    species_probabilities JSONB,
    genus_probabilities JSONB,
    
    is_ood BOOLEAN,
    ood_score FLOAT,
    
    geo_prior_state VARCHAR(100),
    geo_prior_species_probabilities JSONB,
    
    is_calibrated BOOLEAN DEFAULT false,
    model_version VARCHAR(100),
    model_architecture VARCHAR(100),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Clinical evidence
CREATE TABLE clinical_evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    
    syndrome VARCHAR(200),
    clinical_indicators JSONB,
    implicated_genera JSONB,
    rule_version VARCHAR(50),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Clinician review
CREATE TABLE clinician_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    reviewed_by UUID NOT NULL REFERENCES users(id),
    
    accepted_ai_prediction BOOLEAN,
    clinician_diagnosis VARCHAR(500),
    final_species VARCHAR(200),
    final_genus VARCHAR(200),
    confidence_level VARCHAR(50),
    
    clinical_notes TEXT,
    reasoning TEXT,
    antivenom_reference_used VARCHAR(200),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Epidemiological surveillance
CREATE TABLE surveillance_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id),
    
    state VARCHAR(100),
    district VARCHAR(100),
    approximate_coordinates GEOMETRY(Point, 4326),
    
    year INTEGER,
    month INTEGER,
    
    final_species VARCHAR(200),
    final_genus VARCHAR(200),
    venom_category venom_category,
    clinical_syndrome VARCHAR(200),
    severity VARCHAR(50),
    
    outcome VARCHAR(100),
    antivenom_given BOOLEAN,
    
    is_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Audit trail
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action audit_action NOT NULL,
    user_id UUID REFERENCES users(id),
    case_id UUID REFERENCES cases(id),
    target_resource VARCHAR(200),
    target_id VARCHAR(200),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Antivenom facilities
CREATE TABLE antivenom_facilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(300) NOT NULL,
    facility_type VARCHAR(100),
    state VARCHAR(100),
    district VARCHAR(100),
    address TEXT,
    coordinates GEOMETRY(Point, 4326),
    contact_phone VARCHAR(50),
    contact_email VARCHAR(200),
    has_polyvalent_asv BOOLEAN,
    has_icu BOOLEAN,
    notes TEXT,
    last_verified TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_created_by ON cases(created_by);
CREATE INDEX idx_cases_incident_state ON cases(incident_state);
CREATE INDEX idx_surveillance_state ON surveillance_records(state);
CREATE INDEX idx_surveillance_year_month ON surveillance_records(year, month);
CREATE INDEX idx_audit_log_case_id ON audit_log(case_id);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_cases_coordinates ON cases USING GIST(incident_coordinates);
CREATE INDEX idx_surveillance_coordinates ON surveillance_records USING GIST(approximate_coordinates);
CREATE INDEX idx_facilities_coordinates ON antivenom_facilities USING GIST(coordinates);
