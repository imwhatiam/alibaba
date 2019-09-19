import React from 'react';
import PropTypes from 'prop-types';
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap';
import { gettext } from '../../utils/constants';


const propTypes = {
  toggle: PropTypes.func.isRequired,
  item: PropTypes.object.isRequired,
};

class PinganApproveStatusDialog extends React.Component {

  render() {
    return (
      <Modal isOpen={true} toggle={this.props.toggle}>
        <ModalHeader toggle={this.props.toggle}>{gettext('审核状态')}</ModalHeader>
        <ModalBody>
          <div>
            {this.props.item.detailed_approve_status.map((item, idx) => {
              return (
                <li key={idx}>{item[1]}</li>
              )
            })}
          </div>
        </ModalBody>
        <ModalFooter>
          <Button color="secondary" onClick={this.props.toggle}>{gettext('Close')}</Button>
        </ModalFooter>
      </Modal>
    );
  }
}

PinganApproveStatusDialog.propTypes = propTypes;

export default PinganApproveStatusDialog;
