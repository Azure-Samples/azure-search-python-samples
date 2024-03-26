import React from 'react';

import './Result.css';

export default function Result(props) {
    
    return(
    <div className="card result">
        <a href={props.document.url}>
            <img className="card-img-top" src={props.document.imageURL} alt={props.document.description + props.document.partNum}></img>
            <div className="card-body">
                <h6 className="title-style">{props.document.description}</h6>
            </div>
        </a>
    </div>
    );
}
